# IFC Library Creator Module
import ifcopenshell
import uuid
import datetime
from typing import List, Dict, Any, Union
from pathlib import Path

def create_guid():
    """Create a compressed IFC GUID"""
    return ifcopenshell.guid.compress(uuid.uuid4().hex)

def create_ifc_library_from_bauteil_elements(bauteil_elements, output_path):
    """
    Create an IFC library file from extracted BauteilElement objects.
    
    Args:
        bauteil_elements: List of BauteilElement objects
        output_path: Path where the IFC file will be saved
    
    Returns:
        The created IFC file object
    """
    # Create a new IFC file
    ifc_file = ifcopenshell.file()
    
    # Create basic IFC entities
    # Create owner history
    person = ifc_file.create_entity("IfcPerson", 
                                   FamilyName="User", 
                                   GivenName="Default")
    organization = ifc_file.create_entity("IfcOrganization", 
                                         Name="eLCA Material Library Creator")
    person_and_org = ifc_file.create_entity("IfcPersonAndOrganization", 
                                           ThePerson=person, 
                                           TheOrganization=organization)
    application = ifc_file.create_entity("IfcApplication", 
                                        ApplicationDeveloper=organization,
                                        Version="1.0",
                                        ApplicationFullName="eLCA Material Library Creator",
                                        ApplicationIdentifier="eLCA_Creator")
    owner_history = ifc_file.create_entity("IfcOwnerHistory", 
                                          OwningUser=person_and_org,
                                          OwningApplication=application,
                                          ChangeAction="ADDED",
                                          CreationDate=int(datetime.datetime.now().timestamp()))
    
    # Create units
    unit_assignment = ifc_file.create_entity("IfcUnitAssignment")
    
    # Length unit (meters)
    length_unit = ifc_file.create_entity("IfcSIUnit", 
                                        UnitType="LENGTHUNIT", 
                                        Name="METRE")
    unit_assignment.Units = (length_unit,)
    
    # Create project
    project = ifc_file.create_entity("IfcProject", 
                                    GlobalId=create_guid(),
                                    Name="eLCA Material Library",
                                    OwnerHistory=owner_history,
                                    UnitsInContext=unit_assignment)
    
    # Create library information
    library = ifc_file.create_entity("IfcLibraryInformation",
                                    Name="eLCA_Material_Library",
                                    Version="1.0",
                                    Publisher=organization)
    
    # Process each bauteil element
    for element in bauteil_elements:
        # Skip if no components
        if not element.components:
            continue
            
        # Create material layer set with proper name
        layer_set_name = f"{element.category_code} {element.name}"
        material_layer_set = ifc_file.create_entity("IfcMaterialLayerSet", 
                                                   LayerSetName=layer_set_name)
        material_layers = []
        
        # Create material layers for each component
        for idx, component in enumerate(element.components):
            component_name = component.get('name', f'Component_{idx}')
            
            # Try to extract thickness from quantity
            thickness = 0.0
            quantity_text = component.get('quantity', '')
            if quantity_text:
                # Try to parse thickness from quantity (assuming format like "200,00 mm")
                try:
                    # Extract numeric part and convert to float
                    numeric_part = quantity_text.split()[0].replace(',', '.')
                    unit_part = quantity_text.split()[1] if len(quantity_text.split()) > 1 else 'mm'
                    
                    thickness_value = float(numeric_part)
                    
                    # Convert to meters based on unit
                    if unit_part.lower() == 'mm':
                        thickness = thickness_value / 1000.0
                    elif unit_part.lower() == 'cm':
                        thickness = thickness_value / 100.0
                    elif unit_part.lower() == 'm':
                        thickness = thickness_value
                    else:
                        # Default to mm if unit is unknown
                        thickness = thickness_value / 1000.0
                except (ValueError, IndexError):
                    thickness = 0.01  # Default thickness if parsing fails
            
            # Create material
            material = ifc_file.create_entity("IfcMaterial", Name=component_name)
            
            # Add classification reference for UUID if available
            lifecycle_processes = component.get('lifecycle_processes', [])
            if lifecycle_processes:
                for process in lifecycle_processes:
                    process_uuid = process.get('uuid')
                    if process_uuid:

                        # Create external reference to Oekobaudat

                        uuid_value = ifc_file.create_entity('IfcIdentifier', process_uuid)
                        uuid_property = ifc_file.createIfcPropertySingleValue('uuid', 'Uuid form Oekobaudat', uuid_value)

                        extref_value = ifc_file.create_entity('IfcURIReference', f"https://oekobaudat.de/OEKOBAU.DAT/datasetdetail/{process_uuid}")
                        extref_property = ifc_file.createIfcPropertySingleValue(process.get('process_name', 'Unknown'), 'Link to Oekobaudat', extref_value)
                        
                        # Create IfcMaterialProperties
                        pset = ifc_file.create_entity(
                            "IfcMaterialProperties",
                            Name = 'pset_oekobaudat',
                            Material = material,
                            Properties = [uuid_property, extref_property]
                        )
            
            # Create material layer
            material_layer = ifc_file.create_entity(
                "IfcMaterialLayer",
                Material=material,
                LayerThickness=thickness,
                Name=component_name
            )
            
            material_layers.append(material_layer)
        
        # Set the material layers
        if material_layers:
            material_layer_set.MaterialLayers = tuple(material_layers)
            
            # Create a wall type for this material layer set
            wall_type_name = f"{element.category_code} {element.name}"
            wall_type = ifc_file.create_entity(
                "IfcWallType",
                GlobalId=create_guid(),
                OwnerHistory=owner_history,
                Name=wall_type_name,
                Description=f"Wall type for {element.name}",
                ApplicableOccurrence="",
                HasPropertySets=(),
                RepresentationMaps=(),
                Tag="",
                ElementType=wall_type_name,
                PredefinedType="STANDARD"
            )
            
            # Associate the material layer set with the wall type
            ifc_file.create_entity(
                "IfcRelAssociatesMaterial",
                GlobalId=create_guid(),
                OwnerHistory=owner_history,
                RelatedObjects=[wall_type],
                RelatingMaterial=material_layer_set
            )
            
            # Create a relation to the library
            ifc_file.create_entity(
                "IfcRelAssociatesLibrary",
                GlobalId=create_guid(),
                OwnerHistory=owner_history,
                Name=f"Association {element.name}",
                Description=f"Association to library for {element.name}",
                RelatedObjects=[wall_type],  # Only associate the wall type with the library
                RelatingLibrary=library
            )
    
    # Save the IFC file
    ifc_file.write(output_path)
    print(f"IFC library file created at: {output_path}")
    return ifc_file

def attach_library_to_project(ifc_project_path, ifc_library_path):
    """
    Attach a material library to an existing IFC project file.
    
    Args:
        ifc_project_path: Path to the IFC project file
        ifc_library_path: Path to the IFC library file
        
    Returns:
        The modified IFC project file
    """
    try:
        # Load the project file
        project_file = ifcopenshell.open(ifc_project_path)
        
        # Load the library file
        library_file = ifcopenshell.open(ifc_library_path)
        
        # Find the library information in the library file
        library_info = None
        for entity in library_file.by_type("IfcLibraryInformation"):
            library_info = entity
            break
        
        if not library_info:
            print("No library information found in the library file")
            return project_file
        
        # Find the project in the project file
        project = None
        for entity in project_file.by_type("IfcProject"):
            project = entity
            break
        
        if not project:
            print("No project found in the project file")
            return project_file
            
        # Get or create owner history in the project file
        owner_history = None
        if project_file.by_type("IfcOwnerHistory"):
            owner_history = project_file.by_type("IfcOwnerHistory")[0]
        else:
            # Create basic entities if they don't exist
            person = project_file.create_entity("IfcPerson", FamilyName="User", GivenName="Default")
            organization = project_file.create_entity("IfcOrganization", Name="eLCA Material Library Creator")
            person_and_org = project_file.create_entity("IfcPersonAndOrganization", ThePerson=person, TheOrganization=organization)
            application = project_file.create_entity("IfcApplication", ApplicationDeveloper=organization,
                                                   Version="1.0", ApplicationFullName="eLCA Material Library Creator",
                                                   ApplicationIdentifier="eLCA_Creator")
            owner_history = project_file.create_entity("IfcOwnerHistory", OwningUser=person_and_org,
                                                     OwningApplication=application, ChangeAction="ADDED",
                                                     CreationDate=int(datetime.datetime.now().timestamp()))
        
        # Create a new library information in the project file
        new_library_info = project_file.create_entity(
            "IfcLibraryInformation",
            Name=library_info.Name,
            Version=library_info.Version,
            Publisher=project_file.create_entity(
                "IfcOrganization",
                Name=library_info.Publisher.Name
            )
        )
        
        # Find all wall types in the library file
        wall_types = library_file.by_type("IfcWallType")
        
        # Import each wall type and its associated material layer set
        for wall_type in wall_types:
            # Find the material association for this wall type
            material_association = None
            for rel in library_file.by_type("IfcRelAssociatesMaterial"):
                if wall_type.id() in [obj.id() for obj in rel.RelatedObjects]:
                    material_association = rel
                    break
                    
            if not material_association:
                print(f"No material association found for wall type: {wall_type.Name}")
                continue
                
            material_layer_set = material_association.RelatingMaterial
            if not material_layer_set.is_a("IfcMaterialLayerSet"):
                print(f"Material association is not a layer set for wall type: {wall_type.Name}")
                continue
                
            # Create a new material layer set in the project file
            new_mls = project_file.create_entity(
                "IfcMaterialLayerSet",
                LayerSetName=material_layer_set.LayerSetName
            )
            
            # Create new material layers
            new_layers = []
            for layer in material_layer_set.MaterialLayers:
                if not layer or not layer.Material:
                    continue
                    
                # Create a new material
                new_material = project_file.create_entity(
                    "IfcMaterial",
                    Name=layer.Material.Name
                )
                
                # Add classification references if any
                for rel_classification in library_file.by_type("IfcRelAssociatesClassification"):
                    if layer.Material.id() in [obj.id() for obj in rel_classification.RelatedObjects]:
                        ref = rel_classification.RelatingClassification
                        
                        # Create new classification reference
                        new_ref = project_file.create_entity(
                            "IfcClassificationReference",
                            Location=ref.Location,
                            Identification=ref.Identification,
                            Name=ref.Name
                        )
                        
                        # Associate with the new material
                        project_file.create_entity(
                            "IfcRelAssociatesClassification",
                            GlobalId=create_guid(),
                            OwnerHistory=owner_history,
                            RelatedObjects=[new_material],
                            RelatingClassification=new_ref
                        )
                
                # Create a new material layer
                new_layer = project_file.create_entity(
                    "IfcMaterialLayer",
                    Material=new_material,
                    LayerThickness=layer.LayerThickness,
                    Name=layer.Name
                )
                
                new_layers.append(new_layer)
            
            # Set the material layers
            if new_layers:
                new_mls.MaterialLayers = tuple(new_layers)
                
                # Create a new wall type in the project file
                new_wall_type = project_file.create_entity(
                    "IfcWallType",
                    GlobalId=create_guid(),
                    OwnerHistory=owner_history,
                    Name=wall_type.Name,
                    Description=wall_type.Description,
                    ApplicableOccurrence="",
                    HasPropertySets=(),
                    RepresentationMaps=(),
                    Tag="",
                    ElementType=wall_type.ElementType,
                    PredefinedType="STANDARD"
                )
                
                # Associate the material layer set with the wall type
                project_file.create_entity(
                    "IfcRelAssociatesMaterial",
                    GlobalId=create_guid(),
                    OwnerHistory=owner_history,
                    RelatedObjects=[new_wall_type],
                    RelatingMaterial=new_mls
                )
                
                # Associate with the library
                project_file.create_entity(
                    "IfcRelAssociatesLibrary",
                    GlobalId=create_guid(),
                    OwnerHistory=owner_history,
                    Name=f"Association {new_wall_type.Name}",
                    Description=f"Association to library for {new_wall_type.Name}",
                    RelatedObjects=[new_wall_type],
                    RelatingLibrary=new_library_info
                )
        
        # Save the modified project file
        project_file.write(ifc_project_path)
        print(f"Library attached to project file at: {ifc_project_path}")
        return project_file
        
    except Exception as e:
        print(f"Error attaching library to project: {str(e)}")
        import traceback
        traceback.print_exc()
        return None