# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty
from bpy.app.handlers import persistent
import traceback
import os
import tempfile
from pathlib import Path

print("\n[eLCA] Initializing eLCA Bonsai integration...")

# First, ensure dependencies are installed
from . import dependencies
dependencies_installed = dependencies.ensure_dependencies()

# Only import our modules if dependencies are installed
if dependencies_installed:
    # Import our modules
    from . import elca_parser
    from . import ifc_library_creator
    from . import material_sets
else:
    # Create dummy modules for graceful failure
    class DummyModule:
        pass
    
    elca_parser = DummyModule()
    elca_parser.ELCAComponentExtractor = lambda *args, **kwargs: None
    
    ifc_library_creator = DummyModule()
    ifc_library_creator.create_ifc_library_from_bauteil_elements = lambda *args, **kwargs: None
    ifc_library_creator.attach_library_to_project = lambda *args, **kwargs: None
    
    material_sets = DummyModule()
    material_sets.add_material_sets_to_project = lambda *args, **kwargs: None
    material_sets.add_material_sets_from_library_file = lambda *args, **kwargs: None
    material_sets.get_material_sets_summary = lambda *args, **kwargs: {}
    material_sets.remove_material_sets_from_project = lambda *args, **kwargs: None
    material_sets.validate_material_sets = lambda *args, **kwargs: []
    material_sets.sync_material_sets_with_ifc = lambda *args, **kwargs: False

bl_info = {
    "name": "Elca Bonsai",
    "author": "Jakob Beetz",
    "description": "Integration of eLCA data into Blender Bonsai",
    "blender": (2, 80, 0),
    "version": (0, 2, 0),
    "location": "Bonsai > GEOMETRY tab > eLCA",
    "warning": "",
    "category": "Generic",
}

class ELCA_OT_LoadResults(Operator):
    """Load eLCA results from HTML file"""
    bl_idname = "elca.load_results"
    bl_label = "Load eLCA Results (HTML)"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to eLCA results HTML file",
        default="",
        subtype='FILE_PATH'
    )
    
    filter_glob: StringProperty(
        default="*.html;*.htm",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed. Check the console for details.")
            return {'CANCELLED'}
            
        try:
            print(f"[eLCA] Loading eLCA results : {self.filepath}")
            
            # Extract components from HTML file only (no XML yet)
            extractor = elca_parser.ELCAComponentExtractor(self.filepath)
            bauteil_elements = extractor.extract_bauteil_elements()
            
            # Store HTML data for later use
            context.scene["elca_html_path"] = self.filepath
            context.scene["elca_html_data"] = str(len(bauteil_elements))  # Simple count for now
            
            # Report the number of elements found
            num_elements = len(bauteil_elements)
            num_components = sum(len(element.components) for element in bauteil_elements)
            
            self.report({'INFO'}, f"Loaded HTML with {num_elements} building elements and {num_components} components")
            print(f"[eLCA] Loaded HTML with {num_elements} building elements and {num_components} components")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error loading eLCA HTML results: {str(e)}")
            print(f"[eLCA] Error loading eLCA HTML results: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        print("[eLCA] Opening file browser for eLCA HTML results selection")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ELCA_OT_LoadProject(Operator):
    """Load eLCA project XML file and match with HTML data"""
    bl_idname = "elca.load_project"
    bl_label = "Load eLCA Project (XML)"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to eLCA project XML file",
        default="",
        subtype='FILE_PATH'
    )
    
    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed. Check the console for details.")
            return {'CANCELLED'}
            
        try:
            print(f"[eLCA] Loading eLCA project XML from: {self.filepath}")
            
            # Check if HTML has been loaded first
            html_path = context.scene.get("elca_html_path", None)
            if not html_path or not Path(html_path).exists():
                self.report({'ERROR'}, "Please load the HTML results file first!")
                return {'CANCELLED'}
            
            # Store the XML file path
            context.scene["elca_xml_path"] = self.filepath
            
            # Now create extractor with both HTML and XML files
            print(f"[eLCA] Processing both HTML ({html_path}) and XML ({self.filepath}) files")
            extractor = elca_parser.ELCAComponentExtractor(html_path, self.filepath)
            
            # Extract building elements with matched layer thicknesses
            bauteil_elements = extractor.extract_bauteil_elements()
            
            # Get layer thickness summary from XML
            layer_summary = extractor.get_layer_thickness_summary()
            
            # Report results
            num_elements = len(bauteil_elements)
            num_components = sum(len(element.components) for element in bauteil_elements)
            num_layers_with_thickness = 0
            print(f"Calculating number of layers with thickness > 0...")
            for element in bauteil_elements:
                print(f"  Processing Bauteil: {element.name} (Category: {element.category_code})")
                for comp in element.components:
                    thickness = comp.get('layer_thickness')
                    print(f"    Checking Component: {comp.get('name', 'Unnamed Component')} (Thickness: {thickness})")
                    if thickness is not None and thickness > 0:
                        num_layers_with_thickness += 1
                        print(f"      Found layer with thickness > 0. Current count: {num_layers_with_thickness}")
            print(f"Finished calculating. Total layers with thickness > 0: {num_layers_with_thickness}")
            
            if layer_summary.get('total_layers', 0) > 0:
                self.report({'INFO'}, f"Matched {num_layers_with_thickness} components with layer thicknesses from {layer_summary['total_elements']} XML elements")
                print(f"[eLCA] Matched {num_layers_with_thickness} components with layer thicknesses")
                
            #     # Store the matched data
                context.scene["elca_matched_data"] = "true"
                context.scene["elca_layer_data"] = str(layer_summary)
                
            else:
                self.report({'WARNING'}, "No layer thickness data found in XML file")
                print("[eLCA] No layer thickness data found in XML file")
                context.scene["elca_matched_data"] = "false"
            
            # Store the processed bauteil elements for IFC creation
            # We'll serialize this data for the IFC creation step
            try:
                import pickle
                import base64
                serialized_data = base64.b64encode(pickle.dumps(bauteil_elements)).decode('utf-8')
                context.scene["elca_bauteil_elements"] = serialized_data
                print(f"[eLCA] Stored {num_elements} bauteil elements for IFC creation")
            except Exception as e:
                print(f"[eLCA] Could not serialize bauteil elements: {e}")
                context.scene["elca_bauteil_elements"] = ""
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error processing eLCA project: {str(e)}")
            print(f"[eLCA] Error processing eLCA project: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        print("[eLCA] Opening file browser for eLCA project XML selection")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ELCA_OT_ResetData(Operator):
    """Reset all loaded eLCA data"""
    bl_idname = "elca.reset_data"
    bl_label = "Reset eLCA Data"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # Clear all stored eLCA data from scene
            elca_properties = [
                "elca_html_path",
                "elca_xml_path", 
                "elca_html_data",
                "elca_matched_data",
                "elca_layer_data",
                "elca_xml_layer_data",
                "elca_bauteil_elements"
            ]
            
            cleared_count = 0
            for prop in elca_properties:
                if prop in context.scene:
                    del context.scene[prop]
                    cleared_count += 1
            
            print(f"[eLCA] Reset complete - cleared {cleared_count} properties")
            self.report({'INFO'}, f"Reset eLCA data - cleared {cleared_count} stored properties")
            
            # Force UI refresh
            for area in bpy.context.screen.areas:
                if area.type == 'PROPERTIES':
                    area.tag_redraw()
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error resetting eLCA data: {str(e)}")
            print(f"[eLCA] Error resetting eLCA data: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}

class ELCA_OT_CreateIFCLibrary(Operator):
    """Create IFC material library from loaded eLCA data"""
    bl_idname = "elca.create_ifc_library"
    bl_label = "Create IFC Library"
    bl_options = {'REGISTER', 'UNDO'}
    
    attach_to_project: BoolProperty(
        name="Attach to Project",
        description="Attach the created library to the current IFC project",
        default=False
    )
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed. Check the console for details.")
            return {'CANCELLED'}
        
        try:
            # Check if both HTML and XML have been loaded
            html_path = context.scene.get("elca_html_path", None)
            xml_path = context.scene.get("elca_xml_path", None)
            matched_data = context.scene.get("elca_matched_data", "false")
            
            if not html_path:
                self.report({'ERROR'}, "No HTML file loaded. Please load HTML results first.")
                return {'CANCELLED'}
            
            if not xml_path:
                self.report({'ERROR'}, "No XML file loaded. Please load XML project file first.")
                return {'CANCELLED'}
            
            if matched_data != "true":
                self.report({'WARNING'}, "Data matching may not be complete. Proceeding anyway...")
            
            # Retrieve stored bauteil elements
            serialized_data = context.scene.get("elca_bauteil_elements", "")
            if not serialized_data:
                self.report({'ERROR'}, "No processed bauteil elements found. Please reload the XML file.")
                return {'CANCELLED'}
            
            try:
                import pickle
                import base64
                bauteil_elements = pickle.loads(base64.b64decode(serialized_data.encode('utf-8')))
                print(f"[eLCA] Retrieved {len(bauteil_elements)} bauteil elements for IFC creation")
            except Exception as e:
                self.report({'ERROR'}, f"Could not retrieve bauteil elements: {str(e)}")
                return {'CANCELLED'}
            
            # Create output path based on HTML file location
            html_file_path = Path(html_path)
            output_path = html_file_path.with_suffix('.ifc')
            
            # Create the IFC library with layer thickness data
            print(f"[eLCA] Creating IFC library at: {output_path}")
            ifc_file = ifc_library_creator.create_ifc_library_from_bauteil_elements(
                bauteil_elements, str(output_path))
            
            # Count elements with layer thicknesses
            num_elements = len(bauteil_elements)
            num_layers_with_thickness = sum(
                sum(1 for comp in element.components if comp.get('layer_thickness', 0) > 0) 
                for element in bauteil_elements
            )
            
            self.report({'INFO'}, f"Created IFC library with {num_elements} elements ({num_layers_with_thickness} with layer thicknesses) at {output_path}")
            print(f"[eLCA] Created IFC library with {num_elements} elements ({num_layers_with_thickness} with layer thicknesses)")
            
            # Attach to project if requested
            if self.attach_to_project:
                try:
                    project_path = context.scene.BIMProperties.ifc_file if hasattr(context.scene, 'BIMProperties') else None
                    
                    if project_path:
                        # Attach the library to the project
                        ifc_library_creator.attach_library_to_project(project_path, str(output_path))
                        
                        self.report({'INFO'}, f"Attached library to project at {project_path}")
                        print(f"[eLCA] Attached library to project at {project_path}")
                    else:
                        self.report({'WARNING'}, "No active IFC project found to attach library to")
                except Exception as e:
                    self.report({'WARNING'}, f"Could not attach to project: {str(e)}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error creating IFC library: {str(e)}")
            print(f"[eLCA] Error creating IFC library: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}

class ELCA_OT_InstallDependencies(Operator):
    """Install required dependencies for eLCA integration"""
    bl_idname = "elca.install_dependencies"
    bl_label = "Install Dependencies"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            success = dependencies.ensure_dependencies()
            if success:
                self.report({'INFO'}, "All dependencies successfully installed")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to install some dependencies. Check the console for details.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error installing dependencies: {str(e)}")
            print(f"[eLCA] Error installing dependencies: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}

class ELCA_OT_ShowMaterialSets(Operator):
    """Show summary of material sets in the project"""
    bl_idname = "elca.show_material_sets"
    bl_label = "Show Material Sets"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed.")
            return {'CANCELLED'}
            
        try:
            summary = material_sets.get_material_sets_summary()
            
            if summary:
                layer_count = summary.get('total_layer_sets', 0)
                constituent_count = summary.get('total_constituent_sets', 0)
                
                message = f"Found {layer_count} layer sets and {constituent_count} constituent sets"
                self.report({'INFO'}, message)
                print(f"[eLCA] {message}")
                
                # Print detailed info to console
                if layer_count > 0:
                    print("[eLCA] Material Layer Sets:")
                    for layer_set in summary.get('layer_sets', []):
                        print(f"  - {layer_set['name']} ({layer_set['layer_count']} layers, {layer_set['total_thickness']}mm thick)")
                
                if constituent_count > 0:
                    print("[eLCA] Material Constituent Sets:")
                    for const_set in summary.get('constituent_sets', []):
                        print(f"  - {const_set['name']} ({const_set['constituent_count']} constituents)")
            else:
                self.report({'INFO'}, "No material sets found in project")
                print("[eLCA] No material sets found in project")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error getting material sets summary: {str(e)}")
            print(f"[eLCA] Error getting material sets summary: {str(e)}")
            return {'CANCELLED'}

class ELCA_OT_RemoveMaterialSets(Operator):
    """Remove material sets from the project"""
    bl_idname = "elca.remove_material_sets"
    bl_label = "Remove Material Sets"
    bl_options = {'REGISTER', 'UNDO'}
    
    material_type: StringProperty(
        name="Material Type",
        description="Type of material sets to remove",
        default="ALL"
    )
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed.")
            return {'CANCELLED'}
            
        try:
            material_type_filter = None if self.material_type == "ALL" else self.material_type
            material_sets.remove_material_sets_from_project(material_type_filter)
            
            self.report({'INFO'}, f"Removed material sets from project")
            print(f"[eLCA] Removed material sets from project")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error removing material sets: {str(e)}")
            print(f"[eLCA] Error removing material sets: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class ELCA_OT_ValidateMaterialSets(Operator):
    """Validate material sets in the project"""
    bl_idname = "elca.validate_material_sets"
    bl_label = "Validate Material Sets"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed.")
            return {'CANCELLED'}
            
        try:
            issues = material_sets.validate_material_sets()
            
            if not issues:
                self.report({'INFO'}, "All material sets are valid")
                print("[eLCA] All material sets are valid")
            else:
                self.report({'WARNING'}, f"Found {len(issues)} material sets with issues")
                print(f"[eLCA] Found {len(issues)} material sets with issues:")
                
                for issue in issues:
                    if 'error' in issue:
                        print(f"  Error: {issue['error']}")
                    else:
                        print(f"  - {issue['material_name']} ({issue['material_type']}):")
                        for problem in issue['issues']:
                            print(f"    * {problem}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error validating material sets: {str(e)}")
            print(f"[eLCA] Error validating material sets: {str(e)}")
            return {'CANCELLED'}

class ELCA_OT_SyncMaterialSets(Operator):
    """Synchronize material sets with the active IFC file"""
    bl_idname = "elca.sync_material_sets"
    bl_label = "Sync with IFC"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed.")
            return {'CANCELLED'}
            
        try:
            success = material_sets.sync_material_sets_with_ifc()
            
            if success:
                self.report({'INFO'}, "Successfully synchronized material sets with IFC file")
                print("[eLCA] Successfully synchronized material sets with IFC file")
            else:
                self.report({'WARNING'}, "Could not synchronize material sets. Check console for details.")
                print("[eLCA] Could not synchronize material sets")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error synchronizing material sets: {str(e)}")
            print(f"[eLCA] Error synchronizing material sets: {str(e)}")
            return {'CANCELLED'}

# Create our own panel as a fallback
class ELCA_PT_Panel(Panel):
    """eLCA Panel"""
    bl_label = "eLCA Integration"
    bl_idname = "ELCA_PT_Panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="eLCA Integration", icon='FILE_REFRESH')
        
        # Show dependency status
        if not dependencies_installed:
            box.label(text="Dependencies not installed", icon='ERROR')
            box.operator("elca.install_dependencies", icon='PACKAGE')
        else:
            box.label(text="Load eLCA project and results files:")
            row = box.row()
            row.operator("elca.load_results", text="1. Load Results (.html / .htm file) (do this first)", icon='SPREADSHEET')
            
            row = box.row()
            row.operator("elca.load_project", text="2. Load Project (.xml File)", icon='IMPORT')
            
            
            # Material Sets section
            box.separator()
            box.label(text="Material Sets Management:")
            
            row = box.row()
            row.operator("elca.show_material_sets", text="Show Sets", icon='INFO')
            
            row = box.row()
            row.operator("elca.validate_material_sets", text="Validate", icon='CHECKMARK')
            
            row = box.row()
            row.operator("elca.sync_material_sets", text="Sync with IFC", icon='FILE_REFRESH')
            
            row = box.row()
            row.operator("elca.remove_material_sets", text="Remove All", icon='TRASH')

# Store original draw functions
_original_draw_functions = {}

# Draw function for the BIM panel
def draw_elca_ui(self, context):
    try:
        layout = self.layout
        
        box = layout.box()
        box.label(text="eLCA Integration", icon='FILE_REFRESH')
        
        # Show dependency status
        if not dependencies_installed:
            box.label(text="Dependencies not installed", icon='ERROR')
            box.operator("elca.install_dependencies", icon='PACKAGE')
        else:
            # Show file loading status
            html_path = context.scene.get("elca_html_path", None)
            xml_path = context.scene.get("elca_xml_path", None)
            matched_data = context.scene.get("elca_matched_data", "false")
            has_layer_data = context.scene.get("elca_layer_data", None)
            
            # Step 1: HTML Status
            if html_path:
                html_file = Path(html_path).name
                box.label(text=f"✓ HTML loaded: {html_file}", icon='CHECKMARK')
            else:
                box.label(text="1. Load HTML results file", icon='RADIOBUT_OFF')
            
            # Step 2: XML Status  
            if xml_path:
                xml_file = Path(xml_path).name
                if matched_data == "true" and has_layer_data:
                    box.label(text=f"✓ XML loaded: {xml_file}", icon='CHECKMARK')
                    # Try to show layer count
                    try:
                        layer_summary = eval(has_layer_data)
                        layer_count = layer_summary.get('total_layers', 0)
                        element_count = layer_summary.get('total_elements', 0)
                        box.label(text=f"  {element_count} elements, {layer_count} layers matched")
                    except:
                        pass
                else:
                    box.label(text=f"⚠ XML loaded: {xml_file} (no matching)", icon='ERROR')
            else:
                if html_path:
                    box.label(text="2. Load XML project file", icon='RADIOBUT_OFF')
                else:
                    box.label(text="2. Load XML project file", icon='RADIOBUT_OFF')
            
            # File loading buttons
            col = box.column(align=True)
            
            # Step 1: Load HTML
            row = col.row(align=True)
            if html_path:
                row.enabled = False
                row.operator("elca.load_results", text="✓ HTML Loaded", icon='CHECKMARK')
            else:
                row.operator("elca.load_results", text="1. Load Results (HTML)", icon='IMPORT')
            
            # Step 2: Load XML (only enabled after HTML)
            row = col.row(align=True)
            if not html_path:
                row.enabled = False
                row.operator("elca.load_project", text="2. Load Project (XML)", icon='IMPORT')
            elif xml_path and matched_data == "true":
                row.enabled = False
                row.operator("elca.load_project", text="✓ XML Loaded & Matched", icon='CHECKMARK')
            else:
                row.operator("elca.load_project", text="2. Load Project (XML)", icon='IMPORT')
            
            # Step 3: Create IFC Library (only enabled after both files loaded)
            if html_path and xml_path and matched_data == "true":
                col.separator()
                col.label(text="3. Create IFC Library:")
                
                ifc_row = col.row(align=True)
                create_op = ifc_row.operator("elca.create_ifc_library", text="Create IFC Library", icon='PACKAGE')
                
                # Add checkbox for attaching to project
                attach_row = col.row(align=True)
                attach_row.prop(context.scene, "elca_attach_to_project", text="Attach to active project")
            
            # Reset button
            if html_path or xml_path:
                col.separator()
                col.operator("elca.reset_data", text="Reset All Data", icon='X')
        
    except Exception as e:
        print(f"[eLCA] Error in draw_elca_ui: {e}")
        print(traceback.format_exc())

# Function to monkey patch a panel's draw method
def monkey_patch_panel(panel_class, panel_name):
    if panel_name not in _original_draw_functions:
        print(f"[eLCA] Storing original draw function for {panel_name}")
        _original_draw_functions[panel_name] = panel_class.draw
    
    def new_draw(self, context):
        try:
            # Draw our UI first
            draw_elca_ui(self, context)
            # Then call the original draw function
            if panel_name in _original_draw_functions:
                _original_draw_functions[panel_name](self, context)
        except Exception as e:
            print(f"[eLCA] Error in monkey-patched draw function for {panel_name}: {e}")
            print(traceback.format_exc())
            # Fallback to original draw if our addition fails
            if panel_name in _original_draw_functions:
                _original_draw_functions[panel_name](self, context)
    
    print(f"[eLCA] Setting new draw function for {panel_name}")
    panel_class.draw = new_draw

# Persistent handler to add our UI elements after file load
@persistent
def load_handler(dummy):
    print("\n[eLCA] Load handler triggered")
    
    # List all panel classes for debugging
    print("[eLCA] Available Panel classes:")
    # for i, cls in enumerate(bpy.types.Panel.__subclasses__()):
    #     if hasattr(cls, '__module__'):
    #         print(f"  {i+1}. {cls.__module__}.{cls.__name__}")
    
    # Target panel classes to try
    target_panel_classes = [
        "bonsai.bim.module.material.ui.BIM_PT_materials",
        "bonsai.bim.module.material.ui.BIM_PT_object_material",
    ]
    
    found_panel = False
    
    for target_panel_name in target_panel_classes:
        try:
            panel_class = None
            for cls in bpy.types.Panel.__subclasses__():
                if hasattr(cls, '__module__') and f"{cls.__module__}.{cls.__name__}" == target_panel_name:
                    panel_class = cls
                    break
            
            if panel_class:
                print(f"[eLCA] Found panel: {target_panel_name}")
                monkey_patch_panel(panel_class, target_panel_name)
                print(f"[eLCA] Added eLCA UI to {target_panel_name} panel")
                found_panel = True
                break  # Stop after finding one panel
            else:
                print(f"[eLCA] Panel not found: {target_panel_name}")
        
        except Exception as e:
            print(f"[eLCA] Error processing panel {target_panel_name}: {e}")
            print(traceback.format_exc())
    
    if not found_panel:
        print("[eLCA] Could not find any target panels. Using fallback panel.")

def register():
    print("\n[eLCA] Registering eLCA Bonsai integration...")
    
    try:
        bpy.utils.register_class(ELCA_OT_LoadResults)
        print("[eLCA] Registered ELCA_OT_LoadResults")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_LoadResults: {e}")
    
    try:
        bpy.utils.register_class(ELCA_OT_LoadProject)
        print("[eLCA] Registered ELCA_OT_LoadProject")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_LoadProject: {e}")
    
    try:
        bpy.utils.register_class(ELCA_OT_CreateIFCLibrary)
        print("[eLCA] Registered ELCA_OT_CreateIFCLibrary")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_CreateIFCLibrary: {e}")
    
    try:
        bpy.utils.register_class(ELCA_OT_ResetData)
        print("[eLCA] Registered ELCA_OT_ResetData")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_ResetData: {e}")
    
    try:
        bpy.utils.register_class(ELCA_OT_InstallDependencies)
        print("[eLCA] Registered ELCA_OT_InstallDependencies")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_InstallDependencies: {e}")
    
    try:
        bpy.utils.register_class(ELCA_PT_Panel)
        print("[eLCA] Registered ELCA_PT_Panel (fallback panel)")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_PT_Panel: {e}")
    
    # Add scene properties for UI state
    try:
        from bpy.props import BoolProperty
        bpy.types.Scene.elca_attach_to_project = BoolProperty(
            name="Attach to Project",
            description="Attach the created IFC library to the current project",
            default=False
        )
        print("[eLCA] Added scene properties")
    except Exception as e:
        print(f"[eLCA] Error adding scene properties: {e}")
    
    # Add our load handler
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
        print("[eLCA] Added load_handler to load_post")
    
    # Run the load handler immediately
    load_handler(None)
    
    print("[eLCA] Registration complete")

def unregister():
    print("\n[eLCA] Unregistering eLCA Bonsai integration...")
    
    # Restore original draw functions
    for panel_name, original_draw in _original_draw_functions.items():
        try:
            panel_class = None
            for cls in bpy.types.Panel.__subclasses__():
                if hasattr(cls, '__module__') and f"{cls.__module__}.{cls.__name__}" == panel_name:
                    panel_class = cls
                    break
            
            if panel_class:
                panel_class.draw = original_draw
                print(f"[eLCA] Restored original draw function for {panel_name}")
        except Exception as e:
            print(f"[eLCA] Error restoring draw function for {panel_name}: {e}")
    
    # Remove load handler
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
        print("[eLCA] Removed load_handler from load_post")
    
    # Remove scene properties
    try:
        del bpy.types.Scene.elca_attach_to_project
        print("[eLCA] Removed scene properties")
    except Exception as e:
        print(f"[eLCA] Error removing scene properties: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_PT_Panel)
        print("[eLCA] Unregistered ELCA_PT_Panel")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_PT_Panel: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_InstallDependencies)
        print("[eLCA] Unregistered ELCA_OT_InstallDependencies")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_InstallDependencies: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_ResetData)
        print("[eLCA] Unregistered ELCA_OT_ResetData")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_ResetData: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_CreateIFCLibrary)
        print("[eLCA] Unregistered ELCA_OT_CreateIFCLibrary")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_CreateIFCLibrary: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_LoadProject)
        print("[eLCA] Unregistered ELCA_OT_LoadProject")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_LoadProject: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_LoadResults)
        print("[eLCA] Unregistered ELCA_OT_LoadResults")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_LoadResults: {e}")
    
    print("[eLCA] Unregistration complete")

if __name__ == "__main__":
    print("[eLCA] Running as main script")
    register()