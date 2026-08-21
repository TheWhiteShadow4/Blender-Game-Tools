using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using System.IO;
using System.Linq;
using System.Collections.Generic;

// Helper classes for deserializing the JSON
[System.Serializable]
public class MaterialProperty
{
    public string name;
    public string type;
    public float[] value; // For Color
    public float floatValue; // For a single Float
    public string path; // For Texture path
}

[System.Serializable]
public class MaterialData
{
    public string materialName;
    public string shaderName;
    public MaterialProperty[] properties;
}

[System.Serializable]
public class MaterialDataList
{
    public MaterialData[] materials;
    public bool searchProjectMaterials;
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
                        ApplyProperty(material, prop);
                    }
                }

                EditorUtility.SetDirty(material);
                assetsChanged = true;
            }

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
        if (material != null)
            return material;

        // Unsupported shaders can never be created, so always fall back to a name search.
        if (searchProject || string.IsNullOrEmpty(materialData.shaderName))
            return FindMaterialByName(materialData.materialName);

        return null;
    }

    private static Material FindMaterialByName(string materialName)
    {
        string[] guids = AssetDatabase.FindAssets($"{materialName} t:Material");
        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material != null && material.name == materialName)
            {
                return material;
            }
        }
        return null;
    }

    private static void ApplyProperty(Material material, MaterialProperty prop)
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
                    if (string.IsNullOrEmpty(prop.path))
                    {
                        Debug.LogWarning($"Blender Importer: Texture property '{prop.name}' has no path. Skipping property.", material);
                        return;
                    }

                    Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(prop.path);
                    if (tex != null)
                    {
                        material.SetTexture(propertyName, tex);
                    }
                    else
                    {
                        Debug.LogWarning($"Blender Importer: Could not load texture '{prop.path}' for property '{prop.name}'.", material);
                    }
                }
                else
                {
                    Debug.LogWarning($"Blender Importer: Property '{prop.name}' is of type '{propertyType}' on shader '{material.shader.name}', but Blender exported a Texture. Skipping property.", material);
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
