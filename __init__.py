bl_info = {
    "name": "Proxy Names",
    "blender": (2, 80, 0),
    "category": "Interface",
}

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.types import Header, Panel, Operator
from bpy.app.handlers import persistent

class OBJECT_OT_set_proxy_name(bpy.types.Operator):
    bl_idname = "object.set_proxy_name"
    bl_label = "Set Proxy Name"
    bl_options = {'REGISTER', 'UNDO'}

    proxy_name: bpy.props.StringProperty(name="Proxy Name")

    @classmethod
    def poll(cls, context):
        return context.selected_ids is not None and len(context.selected_ids) > 0

    def execute(self, context):
        if not (context.selected_ids is not None and len(context.selected_ids) > 0):
            return {'FINISHED'}

        # IF a bone is selected: last_right_click_type = "DATA" + No Armature + active_bone
        if last_right_click_type == "DATA":
            selected_id = context.selected_ids[-1]
            if not isinstance(selected_id, bpy.types.Armature) and context.active_bone is not None:
                set_proxy_name(self, context.active_bone)
            else:
                set_proxy_name(self, selected_id)
        else:
            selected_id = context.selected_ids[0]
            set_proxy_name(self, selected_id)

        # Update the outliner display
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # IF a bone is selected: last_right_click_type = "DATA" + No Armature + active_bone
        obj = None
        if context.selected_ids is not None and len(context.selected_ids) > 0:
            if last_right_click_type == "DATA":
                selected_id = context.selected_ids[-1]
                if not isinstance(selected_id, bpy.types.Armature) and context.active_bone is not None:
                    obj = context.active_bone
                else:
                    obj = selected_id
            else:
                selected_id = context.selected_ids[0]
                obj = selected_id

        if obj:
            self.proxy_name = obj.get("proxy_name", "")
        else:
            self.proxy_name = ""

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "proxy_name")

def menu_func(self, context):
    layout = self.layout
    layout.operator_context = 'INVOKE_DEFAULT'  # Ensures the operator is invoked
    layout.operator(OBJECT_OT_set_proxy_name.bl_idname)

def menu_func_obj(self, context):
    global last_right_click_type
    last_right_click_type = "OBJECT"
    menu_func(self, context)

def menu_func_data(self, context):
    global last_right_click_type
    last_right_click_type = "DATA"
    menu_func(self, context)

def menu_func_col(self, context):
    global last_right_click_type
    last_right_click_type = "COLLECTION"
    menu_func(self, context)

def set_proxy_name(self, element):
    if self.proxy_name == "":
        element.pop("proxy_name", None)
        if "real_name" in element:
            element.name = element["real_name"]
            element.pop("real_name", None)
    else:
        element["proxy_name"] = self.proxy_name
        if "real_name" not in element:
            element["real_name"] = element.name
    rename_obj(element, False)

# -- CHECKBOX ----------------------------------------------------

def toggle_proxy(value):
    print(f"Proxy toggled. Checkbox value: {value}")
    # Iterate over all attributes of bpy.data
    for attr in dir(bpy.data):
        # Get the actual collection (e.g., objects, meshes, materials, etc.)
        collection = getattr(bpy.data, attr)
        # Ensure it is a collection
        if isinstance(collection, bpy.types.bpy_prop_collection):
            for data_block in collection:
                if isinstance(data_block, bpy.types.ID):
                    rename_obj(data_block, True)
                    # print(f"Name: {data_block.name}, Type: {type(data_block).__name__}")
                    # If data_block is an armature, iterate over its bones
                    if isinstance(data_block, bpy.types.Armature):
                        for bone in data_block.bones:
                            rename_obj(bone, True)
                    

def rename_obj(obj, toggled=False):
    if "proxy_name" not in obj:
        return
    value = bpy.context.window_manager.outliner_checkbox
    if value and obj.name != "#" + obj["proxy_name"]:
        original_name = obj.name
        if toggled: obj["real_name"] = original_name
        obj.name = "#" + obj["proxy_name"]
        print(f"Renamed object '{original_name}' to '{obj.name}'")
    elif obj.name != obj["real_name"]:
        original_name = obj.name
        if toggled: obj["proxy_name"] = original_name.removeprefix("#")
        obj.name = obj["real_name"]
        print(f"Renamed object '{original_name}' back to '{obj.name}'")

# Reference to the original draw method
original_outliner_header_draw = None
last_right_click_type = None

class OUTLINER_HT_header(bpy.types.Header):
    bl_space_type = 'OUTLINER'

    def draw(self, context):
        global original_outliner_header_draw

        layout = self.layout
        wm = context.window_manager

        # Call the original draw method to preserve original header elements
        if original_outliner_header_draw:
            original_outliner_header_draw(self, context)

        # Add a separator and then our custom checkbox
        layout.separator_spacer()
        row = layout.row(align=True)
        row.prop(wm, "outliner_checkbox", text="Proxy", toggle=True)

def checkbox_toggled(self, context):
    value = context.window_manager.outliner_checkbox
    toggle_proxy(value)

# -- CHECKBOX ----------------------------------------------------

def register():
    # Register the operator and add it to the Outliner menus
    bpy.utils.register_class(OBJECT_OT_set_proxy_name)
    bpy.types.OUTLINER_MT_object.append(menu_func_obj) # Edit Object
    bpy.types.OUTLINER_MT_context_menu.append(menu_func_data) # Edit Data
    bpy.types.OUTLINER_MT_collection.append(menu_func_col) # Edit Collection

    # Override the header draw method
    global original_outliner_header_draw
    original_outliner_header_draw = bpy.types.OUTLINER_HT_header.draw
    bpy.types.OUTLINER_HT_header.draw = OUTLINER_HT_header.draw

    # Checkbox
    bpy.types.WindowManager.outliner_checkbox = bpy.props.BoolProperty(
        name="Outliner Checkbox",
        description="Toggle a boolean value and trigger a dummy function",
        default=True,
        update=checkbox_toggled
    )

def unregister():
    # Unregister the operator and remove it from the Outliner menus
    bpy.utils.unregister_class(OBJECT_OT_set_proxy_name)
    bpy.types.OUTLINER_MT_object.remove(menu_func_obj) # Edit Object
    bpy.types.OUTLINER_MT_context_menu.remove(menu_func_data) # Edit Data
    bpy.types.OUTLINER_MT_collection.remove(menu_func_col) # Edit Collection

    # Restore the original header draw method
    global original_outliner_header_draw
    bpy.types.OUTLINER_HT_header.draw = original_outliner_header_draw
    original_outliner_header_draw = None

    # Checkbox
    del bpy.types.WindowManager.outliner_checkbox

if __name__ == "__main__":
    register()