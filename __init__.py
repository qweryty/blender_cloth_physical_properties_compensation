from __future__ import annotations

import bmesh
import bpy

bl_info = {
    'name': 'Correct Cloth Mass',
    'blender': (3, 2, 0),
    'category': 'Physics'
}


def get_real_object_vertices_count(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_obj = obj.evaluated_get(depsgraph)
    return len(evaluated_obj.data.vertices)


def calculate_area(obj, use_modifiers):
    bm = bmesh.new()
    if use_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = obj.evaluated_get(depsgraph)
        data = evaluated_obj.data
    else:
        data = obj.data

    bm.from_mesh(data)
    return sum([f.calc_area() for f in bm.faces])


def get_cloth_modifier(obj):
    for modifier in obj.modifiers:
        if modifier.type == 'CLOTH':
            return modifier
    return None


class ClothMassProperties(bpy.types.PropertyGroup):
    use_modifiers: bpy.props.BoolProperty(
        name='Use Modifiers',
        default=True,
        description='Choose whether to use mass or density.',
        update=ClothMassProperties._update_use_modifiers
    )

    private_mass: bpy.props.FloatProperty(min=0)

    mass: bpy.props.FloatProperty(
        name='Mass',
        unit='MASS',
        description='Total mesh mass independent of vertex count.',
        set=ClothMassProperties._set_mass,
        get=ClothMassProperties._get_mass,
        min=0
    )

    private_density: bpy.props.FloatProperty(min=0)

    density: bpy.props.FloatProperty(
        name='Density',
        description='Density of mesh in kg/m2.',
        set=ClothMassProperties._set_density,
        get=ClothMassProperties._get_density,
        min=0
    )

    def _set_sim(self, obj):
        if self.use_modifiers:
            get_cloth_modifier(obj).settings.mass = self.private_mass / get_real_object_vertices_count(obj)
        else:
            get_cloth_modifier(obj).settings.mass = self.private_mass / len(obj.data.vertices)

    def _update_use_modifiers(self, context):
        obj = self.id_data
        self.private_density = self.private_mass / calculate_area(obj, use_modifiers=self.use_modifiers)
        self._set_sim(obj)

    def _set_mass(self, value):
        self.private_mass = value
        obj = self.id_data
        self.private_density = value / calculate_area(obj, use_modifiers=self.use_modifiers)
        self._set_sim(obj)

    def _get_mass(self):
        return self.private_mass

    def _set_density(self, value):
        self.private_density = value
        obj = self.id_data
        area = calculate_area(obj, use_modifiers=self.use_modifiers)
        self.private_mass = area * value
        self._set_sim(obj)

    def _get_density(self):
        return self.private_density


class ClothMassPanel(bpy.types.Panel):
    bl_label = 'Cloth Mass'
    bl_idname = 'PHYSICS_PT_cloth_mass'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'physics'

    @classmethod
    def poll(cls, context):
        return get_cloth_modifier(context.active_object) is not None

    def draw(self, context):
        layout = self.layout

        obj = context.object

        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'use_modifiers')
        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'mass')
        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'density')


def register():
    bpy.utils.register_class(ClothMassProperties)
    bpy.utils.register_class(ClothMassPanel)
    bpy.types.ClothSettings.correct_cloth_mass = bpy.props.PointerProperty(type=ClothMassProperties)
    bpy.types.Object.correct_cloth_mass = bpy.props.PointerProperty(type=ClothMassProperties)


def unregister():
    bpy.utils.unregister_class(ClothMassPanel)
    bpy.utils.unregister_class(ClothMassProperties)


if __name__ == '__main__':
    register()
