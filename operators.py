import bpy
import gpu
import blf
from . import ui_system

# Global to hold the active popup instance
active_popup = None
draw_handler = None

# Configurable operator prefix (can be set before registration)
OPERATOR_PREFIX = "uitools"

class UITOOLS_OT_custom_popup(bpy.types.Operator):
    bl_idname = "uitools.custom_popup"
    bl_label = "Custom Popup"
    bl_options = {'REGISTER', 'BLOCKING'}

    def __init__(self):
        self.draw_handler = None
        self.space_type = None

    def modal(self, context, event):
        global active_popup
        
        if not active_popup:
            self.remove_handler(context)
            return {'CANCELLED'}

        # Force redraw to keep UI updated
        if self.area:
            self.area.tag_redraw()
        else:
            # Fallback if no area stored
            if context.area:
                context.area.tag_redraw()
            else:
                # Find an area to redraw when context.area is None
                for window in context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
                            break
                    else:
                        continue
                    break

        if event.type == 'TIMER':
            return {'PASS_THROUGH'}

        # Pass event to popup
        # Translate coordinates if the layout region differs from the event region
        if hasattr(self, 'layout_region') and self.layout_region and context.region and self.layout_region != context.region:
            # Translate mouse coordinates from event region to layout region
            original_mouse_x = event.mouse_region_x
            original_mouse_y = event.mouse_region_y
            event.mouse_region_x = event.mouse_region_x + (context.region.x - self.layout_region.x)
            event.mouse_region_y = event.mouse_region_y + (context.region.y - self.layout_region.y)
            handled = active_popup.handle_event(event, context)
            # Restore original coordinates
            event.mouse_region_x = original_mouse_x
            event.mouse_region_y = original_mouse_y
        else:
            handled = active_popup.handle_event(event, context)
        
        # Check if popup wants to close
        if active_popup.finished:
            self.remove_handler(context)
            return {'FINISHED'}
            
        if active_popup.cancelled:
            self.remove_handler(context)
            return {'CANCELLED'}

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            return {'PASS_THROUGH'} 
            
        # Pass through navigation events if not handled
        # This allows rotating/panning the viewport while popup is open
        # ONLY if blocking is False
        if not handled and not active_popup.blocking:
            if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} or \
               (event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and not active_popup.is_inside(event.mouse_region_x, event.mouse_region_y)):
                return {'PASS_THROUGH'}
            
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        global active_popup
        if not active_popup:
            self.report({'ERROR'}, "No active popup definition")
            return {'CANCELLED'}

        try:
            active_popup.update_layout(context)
            
            # Add draw handler to the current space
            self.space = context.space_data
            self.area = context.area  # Store the original area
            if self.space is None:
                # Try to find an available space when context.space_data is None
                # This can happen when called from timers or background threads
                for window in context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            self.space = area.spaces[0]
                            self.area = area  # Store the found area
                            break
                    if self.space:
                        break
                if self.space is None:
                    for window in context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type in ('TEXT_EDITOR', 'CONSOLE'):
                                self.space = area.spaces[0]
                                self.area = area  # Store the found area
                                break
                        if self.space:
                            break
                if self.space is None:
                    self.report({'ERROR'}, "No space available for popup")
                    return {'CANCELLED'}
            
            self.draw_handler = self.space.draw_handler_add(
                self.draw_callback, (context,), 'WINDOW', 'POST_PIXEL'
            )
            
            context.window_manager.modal_handler_add(self)
            if context.area:
                context.area.tag_redraw() # Request initial redraw
            
            # Update layout with the appropriate region
            layout_context = context
            self.layout_region = context.region  # Store the region used for layout
            if self.area and self.area != context.area and self.area.regions:
                # Create a modified context with the correct region for layout
                layout_context = type('Context', (), {})()
                for attr in dir(context):
                    if not attr.startswith('_'):
                        setattr(layout_context, attr, getattr(context, attr))
                layout_context.region = self.area.regions[-1]
                self.layout_region = layout_context.region  # Store the actual region used
            active_popup.update_layout(layout_context)
            
            return {'RUNNING_MODAL'}
        except Exception as e:
            print(f"Failed to show popup: {e}")
            return {'CANCELLED'}

    def draw_callback(self, context):
        global active_popup
        if active_popup:
            # Layout is set once in invoke, no need to update every frame
            active_popup.draw(context)
            active_popup.draw(context)

    def remove_handler(self, context):
        if self.draw_handler and self.space:
            self.space.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None
            self.space = None
        if self.area:
            self.area.tag_redraw()
        else:
            # Fallback if no area stored
            if context.area:
                context.area.tag_redraw()

def show_popup(popup_instance):
    """
    Display a popup.
    
    Args:
        popup_instance: A Popup instance to display
    """
    global active_popup
    active_popup = popup_instance
    try:
        bpy.ops.uitools.custom_popup('INVOKE_DEFAULT')
    except Exception as e:
        print(f"Failed to show popup: {e}")
    
    # Force immediate redraw to ensure popup appears before any blocking code
    try:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    except:
        pass

classes = (
    UITOOLS_OT_custom_popup,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
