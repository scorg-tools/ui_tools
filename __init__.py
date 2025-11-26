"""
UI Tools - Custom Popup System for Blender Addons

A lightweight library for creating custom popups with text input, buttons, and auto-layout.
"""

def register(operator_prefix="uitools"):
    """
    Register the UI Tools operators.
    
    Args:
        operator_prefix: The prefix to use for operator IDs (default: "uitools")
    """
    from . import operators
    operators.OPERATOR_PREFIX = operator_prefix
    operators.register()

def unregister():
    """Unregister the UI Tools operators."""
    from . import operators
    operators.unregister()

def show_popup(popup_instance):
    """Show a popup instance."""
    from .operators import show_popup as _show_popup
    _show_popup(popup_instance)

# Lazy imports using __getattr__ (Python 3.7+)
def __getattr__(name):
    """Lazy load ui_system classes on demand."""
    if name in ('Popup', 'Label', 'Button', 'TextInput', 'Row', 'ProgressBar'):
        from . import ui_system
        return getattr(ui_system, name)
    elif name == 'ThreadManager':
        from . import threading
        return getattr(threading, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['register', 'unregister', 'show_popup', 'Popup', 'Label', 'Button', 'TextInput', 'Row', 'ProgressBar', 'ThreadManager']
