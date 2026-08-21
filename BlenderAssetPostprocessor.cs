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
}

public class BlenderAssetPostprocessor : AssetPostprocessor
{
    // Step 1: Prepare the FBX importer BEFORE it imports the model.
    void OnPreprocessModel()
    {
        string materialJsonPath = assetPath + ".imp.json";
        if (File.Exists(materialJsonPath))
        {
            if (assetImporter is ModelImporter modelImporter)
            {
                modelImporter.useFileScale = false;

                // We create the materials ourselves and remap them via AddRemap in
                // OnPostprocessAllAssets. ImportViaMaterialDescription creates the material
                // slots, which we then remap to our own external materials.
                modelImporter.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;

                // Configure material search to find our newly created materials by name, not texture.
                modelImporter.materialName = ModelImporterMaterialName.BasedOnMaterialName;
                modelImporter.materialSearch = ModelImporterMaterialSearch.RecursiveUp;
            }
        }
    }

    // This method is called after ALL assets have been imported.
    // This is our main entry point to avoid API restrictions.
    static void OnPostprocessAllAssets(string[] importedAssets, string[] deletedAssets, string[] movedAssets, string[] movedFromAssetPaths)
    {
        // Find all imported .imp.json files from our addon.
        var jsonFilesToProcess = new List<string>();
        foreach (string path in importedAssets)
        {
            if (path.EndsWith(".imp.json"))
            {
                jsonFilesToProcess.Add(path);
            }
        }

        if (jsonFilesToProcess.Count == 0) return;

        bool assetsChanged = false;
        var importersToReimport = new HashSet<ModelImporter>();

        foreach(string jsonPath in jsonFilesToProcess)
        {
            // The json file is named like 'path/to/model.fbx.imp.json'.
            // We need to get 'path/to/model.fbx' from that.
            string fbxPath = jsonPath.Substring(0, jsonPath.Length - ".imp.json".Length);

            // Check if the corresponding FBX file exists.
            if (!File.Exists(fbxPath)) continue;

            // Read material data list
            string jsonContent = File.ReadAllText(jsonPath);
            MaterialDataList materialList = JsonUtility.FromJson<MaterialDataList>(jsonContent);

            if (materialList == null || materialList.materials == null || materialList.materials.Length == 0)
            {
                continue;
            }

            string fbxDirectory = Path.GetDirectoryName(fbxPath);
            string materialsDirectoryPath = Path.Combine(fbxDirectory, "Materials");

            // Create the directory if it doesn't exist.
            if (!Directory.Exists(materialsDirectoryPath))
            {
                Directory.CreateDirectory(materialsDirectoryPath);
            }

            // Ensure the FBX importer is available for remapping later
            ModelImporter modelImporter = AssetImporter.GetAtPath(fbxPath) as ModelImporter;

            foreach (var materialData in materialList.materials)
            {
                string materialFileName = materialData.materialName + ".mat";
                string materialPath = Path.Combine(materialsDirectoryPath, materialFileName).Replace('\\', '/');

                Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
                bool isNewMaterial = material == null;

                if (isNewMaterial)
                {
                    // Check if shaderName is null (unsupported material from Blender)
                    if (string.IsNullOrEmpty(materialData.shaderName))
                    {
                        // Try to find existing material in project by name
                        string[] guids = AssetDatabase.FindAssets($"{materialData.materialName} t:Material");
                        if (guids.Length > 0)
                        {
                            string existingMaterialPath = AssetDatabase.GUIDToAssetPath(guids[0]);
                            material = AssetDatabase.LoadAssetAtPath<Material>(existingMaterialPath);
                            Debug.Log($"Blender Importer: Found existing material '{materialData.materialName}' at '{existingMaterialPath}' for unsupported shader.", material);
                        }
                        else
                        {
                            Debug.LogWarning($"Blender Importer: Material '{materialData.materialName}' uses unsupported shader and no existing material found. Skipping.", AssetDatabase.LoadAssetAtPath<Object>(jsonPath));
                            continue; // Skip this material
                        }
                    }
                    else
                    {
                        Debug.Log($"Blender Importer: Creating new material for {jsonPath}");
                        Shader shader = Shader.Find(materialData.shaderName);
                        if (shader == null)
                        {
                            Debug.LogWarning($"Blender Importer: Shader '{materialData.shaderName}' not found. Skipping material '{materialData.materialName}'.", AssetDatabase.LoadAssetAtPath<Object>(jsonPath));
                            continue; // Skip to next material
                        }
                        material = new Material(shader);
                        AssetDatabase.CreateAsset(material, materialPath);
                    }
                }

                // Apply properties
                if (materialData.properties != null)
                {
                    foreach (MaterialProperty prop in materialData.properties)
                    {
                        ApplyProperty(material, prop);
                    }
                }

                EditorUtility.SetDirty(material);
                assetsChanged = true;

                // Now that the material is created/updated, remap the FBX material slot to it.
                if (modelImporter != null)
                {
                    // The FBX material is identified by its type and its name as stored in the
                    // FBX (which matches our Blender material name). SourceAssetIdentifier is a
                    // nested type of AssetImporter.
                    var sourceIdentifier = new AssetImporter.SourceAssetIdentifier(typeof(Material), materialData.materialName);
                    modelImporter.AddRemap(sourceIdentifier, material);
                    importersToReimport.Add(modelImporter);
                }
            }
        }

        // Reimport affected models once, after all remaps are registered.
        // The JSON files are still present at this point so OnPreprocessModel can
        // configure the importer correctly during the reimport.
        foreach (var importer in importersToReimport)
        {
            EditorUtility.SetDirty(importer);
            importer.SaveAndReimport();
        }

        // Clean up the processed json files.
        foreach (string jsonPath in jsonFilesToProcess)
        {
            AssetDatabase.DeleteAsset(jsonPath);
        }

        if (assetsChanged)
        {
            AssetDatabase.SaveAssets();
        }
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
