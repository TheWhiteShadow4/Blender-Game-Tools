using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using System.IO;
using System.Collections.Generic;

// Helper classes for deserializing the JSON
[System.Serializable]
public class MaterialProperty
{
    public string name;
    public string type;
    public float[] value; // For Color
    public float floatValue; // For a single Float
    public int texture; // Index into the top-level textures list (for Texture type)
    public string channel; // Optional channel (R/G/B) for texture channel references
}

[System.Serializable]
public class MaterialData
{
    public string materialName;
    public string shaderName;
    public MaterialProperty[] properties;
}

[System.Serializable]
public class TextureData
{
    public string path;
    public string type;
    public string interpolation;
    public string wrapMode;
}

[System.Serializable]
public class MaterialDataList
{
    public MaterialData[] materials;
    public TextureData[] textures;
    public bool searchProjectMaterials;
    public bool overwriteTextureSettings;
}

public class BlenderAssetPostprocessor : AssetPostprocessor
{
    // Runs BEFORE the model is imported. This is the correct place to set import settings
    // and to remap the FBX material slots to our external materials.
    void OnPreprocessModel()
	{
        if (!(assetImporter is ModelImporter modelImporter))
            return;

        string jsonPath = assetPath + ".imp.json";
        if (!File.Exists(jsonPath))
            return;

        modelImporter.useFileScale = false;
        modelImporter.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        modelImporter.materialName = ModelImporterMaterialName.BasedOnMaterialName;
        modelImporter.materialSearch = ModelImporterMaterialSearch.RecursiveUp;

        MaterialDataList materialList = ReadMaterialList(jsonPath);
        if (materialList == null || materialList.materials == null)
            return;

        string materialsDirectory = Path.Combine(Path.GetDirectoryName(assetPath), "Materials");

        // Materials are created in OnPostprocessAllAssets. On the reimport that follows,
        // they already exist, so we can remap the FBX material slots to them here. Adding
        // remaps during OnPreprocessModel (rather than OnPostprocessAllAssets) avoids
        // Unity's "referencing an asset from the previous import" error.
        foreach (MaterialData materialData in materialList.materials)
        {
            Material material = ResolveExistingMaterial(materialData, materialList.searchProjectMaterials, materialsDirectory);
            if (material != null)
            {
                var identifier = new AssetImporter.SourceAssetIdentifier(typeof(Material), materialData.materialName);
                modelImporter.AddRemap(identifier, material);
            }
        }
    }

    // Runs after all assets have been imported. We create/update the external materials
    // here (which is safe), then schedule a reimport so OnPreprocessModel applies the remaps.
    static void OnPostprocessAllAssets(string[] importedAssets, string[] deletedAssets, string[] movedAssets, string[] movedFromAssetPaths)
	{
        var jsonFilesToProcess = new List<string>();
        foreach (string path in importedAssets)
        {
            if (path.EndsWith(".imp.json"))
            {
                jsonFilesToProcess.Add(path);
            }
        }

		if (jsonFilesToProcess.Count == 0)
			return;

        bool assetsChanged = false;
        var fbxPathsToReimport = new HashSet<string>();

        foreach (string jsonPath in jsonFilesToProcess)
        {
            // The json file is named like 'path/to/model.fbx.imp.json'.
            string fbxPath = jsonPath.Substring(0, jsonPath.Length - ".imp.json".Length);
            if (!File.Exists(fbxPath))
                continue;

            MaterialDataList materialList = ReadMaterialList(jsonPath);
            if (materialList == null || materialList.materials == null || materialList.materials.Length == 0)
                continue;

            string fbxDirectory = Path.GetDirectoryName(fbxPath);
            string materialsDirectory = Path.Combine(fbxDirectory, "Materials");

            if (!Directory.Exists(materialsDirectory))
            {
                Directory.CreateDirectory(materialsDirectory);
            }

            foreach (MaterialData materialData in materialList.materials)
            {
                string materialFileName = materialData.materialName + ".mat";
                string materialPath = Path.Combine(materialsDirectory, materialFileName).Replace('\\', '/');

                Material material = ResolveExistingMaterial(materialData, materialList.searchProjectMaterials, materialsDirectory);

				if (material == null)
				{
					// Unsupported materials (no shader) can only be reused, never created.
					if (string.IsNullOrEmpty(materialData.shaderName))
					{
						Debug.LogWarning($"Blender Importer: Material '{materialData.materialName}' uses unsupported shader and no existing material found. Skipping.", AssetDatabase.LoadAssetAtPath<Object>(jsonPath));
						continue;
					}

					Shader shader = Shader.Find(materialData.shaderName);
					if (shader == null)
					{
						Debug.LogWarning($"Blender Importer: Shader '{materialData.shaderName}' not found. Skipping material '{materialData.materialName}'.", AssetDatabase.LoadAssetAtPath<Object>(jsonPath));
						continue;
					}

					Debug.Log($"Blender Importer: Creating new material '{materialData.materialName}'.");
					material = new Material(shader);
					AssetDatabase.CreateAsset(material, materialPath);
				}

                if (materialData.properties != null)
                {
                    foreach (MaterialProperty prop in materialData.properties)
                    {
                        ApplyProperty(material, prop, materialList.textures);
                    }
                }

                EditorUtility.SetDirty(material);
                assetsChanged = true;
            }

            ApplyTextureSettings(materialList.textures);

            fbxPathsToReimport.Add(fbxPath);
        }

        if (assetsChanged)
        {
            AssetDatabase.SaveAssets();
        }

		// Reimport the affected models on the next editor tick. Remapping happens in
		// OnPreprocessModel; doing the reimport synchronously from here can trigger
		// "AssetImporter is referencing an asset from the previous import".
		foreach (string fbxPath in fbxPathsToReimport)
		{
			string path = fbxPath;
			EditorApplication.delayCall += () =>
			{
				AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);

				// The sidecar JSON has now been consumed by OnPreprocessModel; clean it up.
				string jsonPath = path + ".imp.json";
				if (File.Exists(jsonPath))
				{
					AssetDatabase.DeleteAsset(jsonPath);
				}
			};
		}
    }

    private static MaterialDataList ReadMaterialList(string jsonPath)
    {
        if (!File.Exists(jsonPath))
            return null;

        string jsonContent = File.ReadAllText(jsonPath);
        return JsonUtility.FromJson<MaterialDataList>(jsonContent);
    }

    // Finds an existing material for the given data without creating anything.
    // Order: expected Materials subfolder first, then (optionally) the whole project by name.
    private static Material ResolveExistingMaterial(MaterialData materialData, bool searchProject, string materialsDirectory)
    {
        string materialPath = Path.Combine(materialsDirectory, materialData.materialName + ".mat").Replace('\\', '/');
		Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);

		// Unsupported shaders can never be created, so always fall back to a name search.
		if (material == null && (searchProject || string.IsNullOrEmpty(materialData.shaderName)))
			material = FindMaterialByName(materialData.materialName);

		if (material != null)
		{
			Debug.Log($"Use existing Material: '{materialData.materialName}'.");
			return material;
		}

        return null;
    }

    private static Material FindMaterialByName(string materialName)
    {
        string[] guids = AssetDatabase.FindAssets($"{materialName} t:Material");
        foreach (string guid in guids)
        {
			string path = AssetDatabase.GUIDToAssetPath(guid);
			// Es kann sein, dass hier eine Referenz und nicht das Asset gefunden wird.
			if (!path.EndsWith(".mat")) continue;

			Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material != null && material.name == materialName)
            {
                return material;
            }
        }
        return null;
    }

    private static TextureData ResolveTexturePath(MaterialProperty prop, TextureData[] textures)
    {
        if (textures == null || prop == null || prop.texture < 0 || prop.texture >= textures.Length)
            return null;

       return textures[prop.texture];
    }

    private static void SetTextureOnProperty(Material material, string texturePropertyName, MaterialProperty prop, TextureData[] textures)
    {
		TextureData textureData = ResolveTexturePath(prop, textures);
		if (textureData == null || string.IsNullOrEmpty(textureData.path))
		{
			Debug.LogWarning($"Blender Importer: Texture property '{prop.name}' has no valid texture reference. Skipping property.", material);
			return;
		}

        Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(textureData.path);
        if (tex != null)
		{
			material.SetTexture(texturePropertyName, tex);

			// TODO: Normal Flag auslesen und texture type setzen.
			/*Shader.GetPropertyFlags(material.shader, 0)
            if ((prop.propertyFlags & ShaderPropertyFlags.Normal) != 0)
			{
				textureData.type = "Normal";
				}*/
        }
        else
        {
            Debug.LogWarning($"Blender Importer: Could not load texture '{textureData.path}' for property '{prop.name}'.", material);
        }
    }

	// Applies Unity texture importer settings that are derived from the exported channel usage.
	// For now this only handles "Alpha is Transparency" when the alpha channel is used.
	private static void ApplyTextureSettings(TextureData[] textures)
	{
		if (textures == null)
			return;

		foreach (TextureData texture in textures)
		{
			if (texture == null || string.IsNullOrEmpty(texture.path))
				continue;

			TextureImporter importer = AssetImporter.GetAtPath(texture.path) as TextureImporter;
			if (importer == null)
				continue;

			bool needRefresh = false;

			needRefresh |= MapTextureType(importer, texture);
			needRefresh |= MapTextureInterpolation(importer, texture);
			needRefresh |= MapTextureFlags(importer, texture);

			if (needRefresh)
			{
				EditorUtility.SetDirty(importer);
			}
			importer.SaveAndReimport();
		}
	}

	private static bool MapTextureType(TextureImporter importer, TextureData texture)
	{
		TextureImporterType textureType = importer.textureType;
		switch (texture.type)
		{
			case "Color": textureType = TextureImporterType.Default; break;
			case "Value": textureType = TextureImporterType.Default; break;
			case "Normal": textureType = TextureImporterType.NormalMap; break;
		}
		if (importer.textureType != textureType)
		{
			importer.textureType = textureType;
			return true;
		}
		return false;
	}

	private static bool MapTextureInterpolation(TextureImporter importer, TextureData texture)
	{
		FilterMode filterMode = importer.filterMode;
		switch (texture.interpolation)
		{
			case "Point": filterMode = FilterMode.Point; break;
			case "Cubic": filterMode = FilterMode.Trilinear; break;
			case "Smart": filterMode = FilterMode.Trilinear; break;
			default: filterMode = FilterMode.Bilinear; break;
		}
		if (filterMode != importer.filterMode)
		{
			importer.filterMode = filterMode;
			return true;
		}
		return false;
	}

	private static bool MapTextureFlags(TextureImporter importer, TextureData texture)
	{
		bool needRefresh = false;
		if (texture.type != "Color" && importer.sRGBTexture)
		{
			importer.sRGBTexture = false;
			needRefresh = true;
		}

		if (texture.type == "Color" && !importer.alphaIsTransparency)
		{
			importer.alphaIsTransparency = true;
			needRefresh = true;
		}
		return needRefresh;
	}

    // Finds a texture property whose name shares the given base name and ends with "Map".
    // Used as a best-effort fallback when a Blender texture property maps to a non-texture
    // shader property (e.g. "Metallic" -> "_MetallicGlossMap").
    private static string FindTextureMapProperty(Shader shader, string propertyName)
    {
        if (shader == null || string.IsNullOrEmpty(propertyName))
            return null;

        string baseName = propertyName.TrimStart('_');

        int count = shader.GetPropertyCount();
        for (int i = 0; i < count; i++)
        {
            if (shader.GetPropertyType(i) != ShaderPropertyType.Texture)
                continue;

            string name = shader.GetPropertyName(i);
            string trimmed = name.TrimStart('_');

            if (trimmed.EndsWith("Map", System.StringComparison.OrdinalIgnoreCase) &&
                trimmed.StartsWith(baseName, System.StringComparison.OrdinalIgnoreCase))
            {
                return name;
            }
        }

        return null;
    }

    private static void ApplyProperty(Material material, MaterialProperty prop, TextureData[] textures)
    {
        if (material == null || prop == null || string.IsNullOrEmpty(prop.name))
        {
            return;
        }

        if (!TryResolveProperty(material, prop.name, out string propertyName, out ShaderPropertyType propertyType))
        {
            Debug.LogWarning($"Blender Importer: Property '{prop.name}' (or '_{prop.name}') not found on shader '{material.shader.name}'. Skipping property.", material);
            return;
        }

        switch (prop.type)
        {
            case "Color":
                if (prop.value == null || prop.value.Length < 4)
                {
                    Debug.LogWarning($"Blender Importer: Property '{prop.name}' has no valid color value. Skipping property.", material);
                    return;
                }

                if (propertyType == ShaderPropertyType.Color)
                {
                    material.SetColor(propertyName, new Color(prop.value[0], prop.value[1], prop.value[2], prop.value[3]));
                }
                else if (propertyType == ShaderPropertyType.Vector)
                {
                    material.SetVector(propertyName, new Vector4(prop.value[0], prop.value[1], prop.value[2], prop.value[3]));
                }
                else
                {
                    Debug.LogWarning($"Blender Importer: Property '{prop.name}' is of type '{propertyType}' on shader '{material.shader.name}', but Blender exported a Color. Skipping property.", material);
                }
                break;

            case "Float":
                if (propertyType == ShaderPropertyType.Float || propertyType == ShaderPropertyType.Range)
                {
                    material.SetFloat(propertyName, prop.floatValue);
                }
                else
                {
                    Debug.LogWarning($"Blender Importer: Property '{prop.name}' is of type '{propertyType}' on shader '{material.shader.name}', but Blender exported a Float. Skipping property.", material);
                }
                break;

            case "Texture":
                if (propertyType == ShaderPropertyType.Texture)
                {
                    SetTextureOnProperty(material, propertyName, prop, textures);
                }
                else
                {
                    // Best-effort fallback: the Blender property is a texture, but the
                    // matching shader property is not (e.g. a float/range). Look for a
                    // texture property with a "Map" suffix that shares the base name
                    // (e.g. "Metallic" -> "_MetallicGlossMap").
                    string texturePropertyName = FindTextureMapProperty(material.shader, propertyName);
                    if (!string.IsNullOrEmpty(texturePropertyName))
                    {
                        Debug.LogWarning($"Blender Importer: Property '{prop.name}' is of type '{propertyType}' on shader '{material.shader.name}', but Blender exported a Texture. Remapping to texture property '{texturePropertyName}'.", material);
                        SetTextureOnProperty(material, texturePropertyName, prop, textures);
                    }
                    else
                    {
                        Debug.LogWarning($"Blender Importer: Property '{prop.name}' is of type '{propertyType}' on shader '{material.shader.name}', but Blender exported a Texture. Skipping property.", material);
                    }
                }
                break;

            default:
                Debug.LogWarning($"Blender Importer: Unknown property type '{prop.type}' for '{prop.name}'. Skipping property.", material);
                break;
        }
    }

    private static bool TryResolveProperty(Material material, string requestedName, out string propertyName, out ShaderPropertyType propertyType)
    {
        propertyName = null;
        propertyType = default;

        if (material == null || material.shader == null || string.IsNullOrEmpty(requestedName))
            return false;

        Shader shader = material.shader;
        string underscoredName = "_" + requestedName;

        // Match against the shader's actual properties by comparing both the reference name
        // (e.g. "_BaseColor") and the display name (e.g. "Base Color") case-insensitively.
        // This avoids the ambiguity of Material.HasProperty/Shader.FindPropertyIndex with
        // respect to the leading underscore.
        int propertyCount = shader.GetPropertyCount();
        for (int i = 0; i < propertyCount; i++)
        {
            string referenceName = shader.GetPropertyName(i);
            string description = shader.GetPropertyDescription(i);

            if (string.Equals(referenceName, requestedName, System.StringComparison.OrdinalIgnoreCase) ||
                string.Equals(referenceName, underscoredName, System.StringComparison.OrdinalIgnoreCase) ||
                string.Equals(description, requestedName, System.StringComparison.OrdinalIgnoreCase) ||
                string.Equals(description, underscoredName, System.StringComparison.OrdinalIgnoreCase))
            {
                propertyName = referenceName;
                propertyType = shader.GetPropertyType(i);
                return true;
            }
        }

        return false;
    }
}
