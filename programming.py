bl_info = {"name": "Template", "category": "Node"}
import copy
import math
import json
import bpy
from bpy.props import StringProperty, IntProperty, PointerProperty, FloatProperty, FloatVectorProperty, CollectionProperty, BoolProperty, EnumProperty
from bpy.types import NodeTree, Node, NodeLinks, NodeSocket, PropertyGroup, Text, Function, ID, Property
import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem

def get_input(caller, name): 
    if name not in caller.inputs:
        return None
    sock = caller.inputs[name]
    inp = None
    defval = None
    if sock.is_linked and len(sock.links) > 0 and sock.links[0].is_valid:
        defval = sock.links[0].from_socket.default_value
    else:
        defval = sock.default_value
    if hasattr(defval, "value"):
        inp = defval.value
    else:
        inp = defval
    return inp

def update_chain(socket):
    if socket.is_linked:
        for link in socket.links:
            if link.is_valid:
                link.to_node.update()

def update_value(lst, name, src):
    if hasattr(lst, "outputs"):
        lst = lst.outputs
    if hasattr(lst[name], "default_value"):
        if hasattr(lst[name].default_value, "value"):
            if lst[name].default_value.value != src:
                lst[name].default_value.value = src
                update_chain(lst[name])
        else:
            if lst[name].default_value != src:
                lst[name].default_value = src
                update_chain(lst[name])
    else:
        if lst[name] != src:
            lst[name] = src

class ProgrammingNodeTree(NodeTree):
    """Programming Node Tree"""
    bl_idname = "ProgrammingNodeTree"
    bl_label = "Programming Node Tree"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, ntree):
        return True

class CustomProperty(PropertyGroup):
    node = StringProperty(name="node", default="")
    is_output = BoolProperty(name="is_output", default=False)

    def callback(self, node, is_output=False):
        self.node = node
        self.is_output = is_output

    def update(self, context):
        if not self.is_output:
            if self.node in self.id_data.nodes:
                self.id_data.nodes[self.node].update()
            else:
                print("update not initialised ", self.is_output, " ", self.node)

    value = StringProperty(default = "", update=update)

    def template_layout(self, layout):
        row = layout.row(align=True)
        row.prop(self, "value", text="Value")

class StringSocket(NodeSocket):
    """String Socket"""
    bl_idname = "StringSocket"
    bl_label = "String"

    def callback(self):
        if hasattr(self.default_value, "callback"): #if custom default_value property
            self.default_value.callback(self.node.name, self.is_output) 

    def update(self, context):
        if not self.is_output:
            self.node.update()

    #default_value = StringProperty(name="default_value", update=update)
    default_value = PointerProperty(type=CustomProperty, name="default_value", update=update)

    def draw(self, context, layout, node, text):
        if self.is_output or self.is_linked:
            layout.label(text)
        else:
            if hasattr(self.default_value, "template_layout"):
                self.default_value.template_layout(layout)
            else:
                row = layout.row(align=True)
                row.prop(self, "default_value", text="Value")

    def draw_color(self, context, node):
        return (0.01, 0.5, 0.08, 1.0)

class TextFileOutputNode(Node, ProgrammingNodeTree):
    """Text File Output Node"""
    bl_idname = "TextFileOutputNode"
    bl_label = "Text File Output"
    bl_icon = "OBJECT_DATA"

    def uda(self, context):
        self.update()

    tfile = PointerProperty(type=Text, name="tfile", update=uda)

    def init(self, context):
        self.inputs.new("StringSocket", "Text").callback()

    def update(self):
        text = get_input(self, "Text")
        if self.tfile is not None:
            self.tfile.clear()
            self.tfile.write(text)

    def copy(self, node):
        print("Copying from node ", node)
        for inp in self.inputs:
            if hasattr(inp, "callback"):
                inp.callback()
        for outp in self.outputs:
            if hasattr(outp, "callback"):
                outp.callback()

    def free(self):
        print("Removing node ", self, ", Goodbye!")

    def draw_buttons(self, context, layout):
        layout.template_ID(self, "tfile", new="text.new", unlink="text.unlink", open="text.open")

    def draw_label(self):
        return "Text File Output"

class TextFileInputNode(Node, ProgrammingNodeTree):
    """Text File Input Node"""
    bl_idname = "TextFileInputNode"
    bl_label = "Text File Input"
    bl_icon = "OBJECT_DATA"

    def uda(self, context):
        self.update()

    tfile = PointerProperty(type=Text, name="tfile", update=uda)

    def init(self, context):
        self.outputs.new("StringSocket", "String").callback()

    def update(self):
        if self.tfile is not None:
            update_value(self, "String", self.tfile.as_string())

    def copy(self, node):
        print("Copying from node ", node)
        for inp in self.inputs:
            if hasattr(inp, "callback"):
                inp.callback()
        for outp in self.outputs:
            if hasattr(outp, "callback"):
                outp.callback()

    def free(self):
        print("Removing node ", self, ", Goodbye!")

    def draw_buttons(self, context, layout):
        layout.template_ID(self, "tfile", new="text.new", unlink="text.unlink", open="text.open")

    def draw_label(self):
        return "Text File Input"


class JSONToNode(Node, ProgrammingNodeTree):
    """JSON To Node"""
    bl_idname = "JSONToNode"
    bl_label = "JSON To Node"
    bl_icon = "OBJECT_DATA"

    def uda(self, context):
        self.update()

    prevtext = StringProperty(name="prevtext", default="")

    def init(self, context):
        self.inputs.new("StringSocket", "Text").callback()
        self.inputs.new("NodeSocketInt", "Int").callback()
        self.outputs.new("NodeSocketInt", "oInt").callback()

    def update(self):
        text = self.prevtext
        self.prevtext = get_input(self, "Text") # StringPropertys mess with formatting
        if self.prevtext != text:
            text = self.prevtext
            self.outputs.clear()
            j = json.loads(text)
            if "Node" in j:
                node = j["Node"]
                if "Output" in node:
                    for out in node["Output"]:
                        output = self.outputs.new(out["Type"], out["Name"])
                        if hasattr(output, "callback"):
                            output.callback()
                        if "Value" in out:
                            update_value(self, out["Name"], out["Value"])

    def copy(self, node):
        print("Copying from node ", node)
        for inp in self.inputs:
            if hasattr(inp, "callback"):
                inp.callback()
        for outp in self.outputs:
            if hasattr(outp, "callback"):
                outp.callback()

# class BlankSocket(NodeSocket):
#     """Blank Socket"""
#     bl_idname = "BlankSocket"
#     bl_label = "Blank"

#     def callback(self):
#         if hasattr(self.default_value, "callback"): #if custom default_value property
#             self.default_value.callback(self.node.name, self.is_output) 

#     def update(self, context):
#         if not self.is_output:
#             self.node.update()

#     default_value = IntProperty(default=0, name="default_value", update=uda)

#     def draw(self, context, layout, node, text):
#         if self.is_output or self.is_linked:
#             layout.label(text)
#         else:
#             if hasattr(self.default_value, "template_layout"):
#                 self.default_value.template_layout(layout)
#             else:
#                 row = layout.row(align=True)
#                 row.prop(self, "default_value", text="Value")

#     def draw_color(self, context, node):
#         return (0.01, 0.5, 0.08, 1.0)

class CallbackOperator(bpy.types.Operator):
    bl_idname = "custom.callback"
    bl_label = "IO Manager"

    options = {}
    identity = StringProperty(name="identity", default="")

    def invoke(self, context, event):
        CallbackOperator.options[self.properties["identity"]]["callback"](
            CallbackOperator.options[self.properties["identity"]]
        )
        return {"FINISHED"}

class DynamicNode(Node, ProgrammingNodeTree):
    """Dynamic Node"""
    bl_idname = "DynamicNode"
    bl_label = "Dynamic"
    bl_icon = "OBJECT_DATA"

    def uda(self, context):
        self.update()

    active_input = IntProperty(name="active_input", default=0)
    active_output = IntProperty(name="active_output", default=0)

    def init(self, context):
        self.inputs.new("NodeSocketInt", "IntIn")
        self.inputs.new("NodeSocketInt", "IntIn2")
        #self.inputs.new("BlankSocket", "BlankIn").callback()
        self.outputs.new("NodeSocketInt", "IntOut")
        #self.outputs.new("BlankSocket", "BlankOut").callback()

    def update(self):
        #self.outputs["BlankOut"].default_value.value = 0
        #self.update_chain("BlankOut")
        print("update")

    def copy(self, node):
        print("Copying from node ", node)
        for inp in self.inputs:
            if hasattr(inp, "callback"):
                inp.callback()
        for outp in self.outputs:
            if hasattr(outp, "callback"):
                outp.callback()

    def free(self):
        print("Removing node ", self, ", Goodbye!")

    #def draw_buttons(self, context, layout):
        #layout.label("")

    def operator_callback(self, value):
        print(value)
        active = None
        inp = value["type"] == "inputs"
        outp = value["type"] == "outputs"
        if inp:
            active = self.active_input
        elif outp:
            active = self.active_output

        if value["action"] == 'ADD' and inp:
            ty = "NodeSocketInt"
            name = "Val"
            if len(self.inputs) > active:
                ty = self.inputs[active].bl_idname
                name = self.inputs[active].name
            sock = self.inputs.new(ty, name)
            if hasattr(sock, "callback"):
                sock.callback()
            self.active_input = active + 1
        elif value["action"] == 'ADD' and outp:
            ty = "NodeSocketInt"
            name = "Val"
            if len(self.outputs) > active:
                ty = self.outputs[active].bl_idname
                name = self.outputs[active].name
            sock = self.outputs.new(ty, name)
            if hasattr(sock, "callback"):
                sock.callback()
            self.active_output = active + 1
        
        elif value["action"] == 'REMOVE' and inp and len(self.inputs) > active:
            self.inputs.remove(self.inputs[active])
            if len(self.inputs) == 0:
                self.active_input = 0
            elif active == len(self.inputs):
                self.active_input = len(self.inputs)-1
        elif value["action"] == 'REMOVE' and outp and len(self.outputs) > active:
            self.outputs.remove(self.outputs[active])
            if len(self.outputs) == 0:
                self.active_output = 0
            elif active == len(self.outputs):
                self.active_output = len(self.outputs)-1

        elif value["action"] == 'UP' and inp and len(self.inputs) > active and active > 0:
            self.inputs.move(active, active - 1)
            self.active_input = active - 1
        elif value["action"] == 'UP' and outp and len(self.outputs) > active and active > 0:
            self.outputs.move(active, active - 1)
            self.active_output = active - 1

        elif value["action"] == 'DOWN' and inp and (len(self.inputs) - 1) > active:
            self.inputs.move(active, active + 1)
            self.active_input = active + 1
        elif value["action"] == 'DOWN' and outp and (len(self.outputs) - 1) > active:
            self.outputs.move(active, active + 1)
            self.active_output = active + 1


    def draw_buttons_ext(self, context, layout):
        row = layout.row(align=True)
        row.template_list("NODE_UL_interface_sockets", "", self, "inputs", self, "active_input")
        col = row.column(align=True)
        
        op = col.operator("custom.callback", icon="ZOOMIN", text="")
        op.identity = self.name + "1"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'ADD', "type":"inputs"}

        op = col.operator("custom.callback", icon="ZOOMOUT", text="")
        op.identity = self.name + "2"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'REMOVE', "type":"inputs"}

        col.separator()

        op = col.operator("custom.callback", icon="TRIA_UP", text="")
        op.identity = self.name + "3"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'UP', "type":"inputs"}

        op = col.operator("custom.callback", icon="TRIA_DOWN", text="")
        op.identity = self.name + "4"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'DOWN', "type":"inputs"}
        
        row.separator()

        row.template_list("NODE_UL_interface_sockets", "", self, "outputs", self, "active_output")
        col = row.column(align=True)
        
        op = col.operator("custom.callback", icon="ZOOMIN", text="")
        op.identity = self.name + "5"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'ADD', "type":"outputs"}

        op = col.operator("custom.callback", icon="ZOOMOUT", text="")
        op.identity = self.name + "6"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'REMOVE', "type":"outputs"}

        col.separator()

        op = col.operator("custom.callback", icon="TRIA_UP", text="")
        op.identity = self.name + "7"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'UP', "type":"outputs"}

        op = col.operator("custom.callback", icon="TRIA_DOWN", text="")
        op.identity = self.name + "8"
        CallbackOperator.options[op.identity] = {"callback":self.operator_callback, "action":'DOWN', "type":"outputs"}

class CustomNodeCategory(NodeCategory):
    @classmethod
    def poll(cls,context):
        return True #context.space_data.tree_type == "ABCCustomNodeCategory"

node_categories = [
    CustomNodeCategory(
        "CUSTOM",
        "Custom",
        items = [
            NodeItem("TextFileInputNode"),
            NodeItem("TextFileOutputNode"),
            NodeItem("JSONToNode"),
            NodeItem("DynamicNode")
        ]
    )
]

registered = False

def register():
    bpy.utils.register_class(ProgrammingNodeTree)
    bpy.utils.register_class(CustomProperty)
    bpy.utils.register_class(CallbackOperator)
    #bpy.utils.register_class(BlankSocket)
    bpy.utils.register_class(DynamicNode)
    bpy.utils.register_class(StringSocket)
    bpy.utils.register_class(TextFileInputNode)
    bpy.utils.register_class(TextFileOutputNode)
    bpy.utils.register_class(JSONToNode)
    nodeitems_utils.register_node_categories("CUSTOM", node_categories)
    registered = True

def unregister(): 
    nodeitems_utils.unregister_node_categories("CUSTOM")
    bpy.utils.unregister_class(ProgrammingNodeTree)
    bpy.utils.unregister_class(CustomProperty)
    bpy.utils.unregister_class(CallbackOperator)
    # bpy.utils.unregister_class(BlankSocket)
    bpy.utils.unregister_class(DynamicNode)
    bpy.utils.unregister_class(StringSocket)
    bpy.utils.unregister_class(TextFileInputNode)
    bpy.utils.unregister_class(TextFileOutputNode)
    bpy.utils.unregister_class(JSONToNode)
    registered = False

if __name__ == "__main__" :  
    try:
        unregister()
    except:
        print("failed to unregister")
    try:
        register()
    except:
        print("failed to register")