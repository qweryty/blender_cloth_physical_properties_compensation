from __future__ import annotations

import bmesh
import bpy
from bpy.app.handlers import persistent

bl_info = {
    'name': 'Cloth Physical Properties Compensation',
    'description': 'Adds replacement settings for physical properties that will compensate for '
                   'changes in vertex count and area',
    'category': 'Physics',
    'version': (0, 1, 0),
    'author': 'Sergey Morozov',
    'blender': (3, 2, 0),
    'location': 'Properties > Physics Properties',
    'tracker_url':
        'https://github.com/qweryty/blender_cloth_physical_properties_compensation/issues',
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
        update=ClothMassProperties._update
    )

    enabled: bpy.props.BoolProperty(
        name='Enabled',
        description='Enable mass compensation.',
        default=True,
        update = ClothMassProperties._update
    )

    private_mass: bpy.props.FloatProperty(min=0, default=-1.0)

    mass: bpy.props.FloatProperty(
        name='Mass',
        unit='MASS',
        description='Total mesh mass independent of vertex count.',
        set=ClothMassProperties._set_mass,
        get=ClothMassProperties._get_mass,
        min=0
    )

    private_density: bpy.props.FloatProperty(min=0, default=10)

    density: bpy.props.FloatProperty(
        name='Density',
        description='Density of mesh in kg/m2.',
        set=ClothMassProperties._set_density,
        get=ClothMassProperties._get_density,
        min=0,
    )

    air_viscosity: bpy.props.FloatProperty(
        name='Air Viscosity',
        description='Air Viscosity',
        min=0,
        default=1,
        update=ClothMassProperties._update
    )

    def set_sim(self):
        if not self.enabled:
            return

        obj = self.id_data
        cloth_modifier = get_cloth_modifier(obj)
        if not cloth_modifier:
            return

        cloth_modifier_settings = cloth_modifier.settings
        if self.use_modifiers:
            cloth_modifier_settings.mass = self.private_mass / get_real_object_vertices_count(obj)
        else:
            cloth_modifier_settings.mass = self.private_mass / len(obj.data.vertices)

        cloth_modifier_settings.air_damping = self.air_viscosity * cloth_modifier_settings.mass

    def _update(self, context):
        obj = self.id_data
        self.private_mass = self.private_density * calculate_area(obj, use_modifiers=self.use_modifiers)
        self.set_sim()

    def _set_mass(self, value):
        self.private_mass = value
        obj = self.id_data
        self.private_density = value / calculate_area(obj, use_modifiers=self.use_modifiers)
        self.set_sim()

    def _get_mass(self):
        if self.private_mass < 0:
            obj = self.id_data
            self.private_mass = self.private_density * calculate_area(obj, use_modifiers=self.use_modifiers)
        return self.private_mass

    def _set_density(self, value):
        self.private_density = value
        obj = self.id_data
        area = calculate_area(obj, use_modifiers=self.use_modifiers)
        self.private_mass = area * value
        self.set_sim()

    def _get_density(self):
        return self.private_density


class PhysicalPropertiesCompensationPanel(bpy.types.Panel):
    bl_label = 'Physical Properties Compensation'
    bl_idname = 'PHYSICS_PT_physical_properties_compensation'
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
        row.prop(obj.correct_cloth_mass, 'enabled')

        if not obj.correct_cloth_mass.enabled:
            return

        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'use_modifiers')
        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'mass')
        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'density')
        row = layout.row()
        row.prop(obj.correct_cloth_mass, 'air_viscosity')


depsgraph_post_running = False


@persistent
def depsgraph_post_handler(post):
    global depsgraph_post_running
    active_object = bpy.context.active_object
    if depsgraph_post_running or not active_object or not active_object.correct_cloth_mass:
        return

    depsgraph_post_running = True
    active_object.correct_cloth_mass.set_sim()
    depsgraph_post_running = False


def register():
    bpy.utils.register_class(ClothMassProperties)
    bpy.utils.register_class(PhysicalPropertiesCompensationPanel)
    bpy.types.Object.correct_cloth_mass = bpy.props.PointerProperty(type=ClothMassProperties)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_post_handler)


def unregister():
    bpy.utils.unregister_class(PhysicalPropertiesCompensationPanel)
    bpy.utils.unregister_class(ClothMassProperties)
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_post_handler)


if __name__ == '__main__':
    register()
