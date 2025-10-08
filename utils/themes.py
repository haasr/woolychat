THEMES = {
    'ocean_breeze': {
        'header_gradient_left': '#72dddd',
        'header_gradient_right': '#86c3f9',
        'bg_gradient_left': '#60c1e7',
        'bg_gradient_right': '#7fc9e2'
    },
    'golden': {
        'header_gradient_left': '#e9a508',
        'header_gradient_right': '#ffcb46',
        'bg_gradient_left': '#1362b1',
        'bg_gradient_right': '#52a1ef'
    },
    'autumn': {
        'header_gradient_left': '#cd5a08',
        'header_gradient_right': '#f98a3a',
        'bg_gradient_left': '#703d39',
        'bg_gradient_right': '#a13670'
    },
    'midnight': {
        'header_gradient_left': '#283593',
        'header_gradient_right': '#3a0080',
        'bg_gradient_left': '#10105c',
        'bg_gradient_right': '#2d2d8a'
    },
    'cyberpunk': {
        'header_gradient_left': '#9c27b0',
        'header_gradient_right': '#e91e63',
        'bg_gradient_left': '#16a0a0',
        'bg_gradient_right': '#494949'
    },
    'vinyl': {
        'header_gradient_left': '#b71c1c',
        'header_gradient_right': '#cc0000',
        'bg_gradient_left': '#333333',
        'bg_gradient_right': '#444444'
    },
    'koala': {
        'header_gradient_left': '#8d9db6',
        'header_gradient_right': '#a8b5c8',
        'bg_gradient_left': '#7d8471',
        'bg_gradient_right': '#9db4a0'
    },
    'pink': {
        'header_gradient_left': '#FF69B4',
        'header_gradient_right': '#FF81A6',
        'bg_gradient_left': '#F48FB1',
        'bg_gradient_right': '#E9967A'
    },
    'forest': {
        'header_gradient_left': '#3a8673',
        'header_gradient_right': '#2d6a4f',
        'bg_gradient_left': '#2d6a4f',
        'bg_gradient_right': '#3a8658'
    },
    'moonlit_lilac': {
        'header_gradient_left': '#667eea',
        'header_gradient_right': '#764ba2',
        'bg_gradient_left': '#1e3a8a',
        'bg_gradient_right': '#294a8b'
    },
    'summer_sunset': {
        'header_gradient_left': '#e9c46a',
        'header_gradient_right': '#f4a261',
        'bg_gradient_left': "#f16236",
        'bg_gradient_right': "#ee952f"
    },
    'ryan': {
        'header_gradient_left': "#e3b84b",
        'header_gradient_right': "#e6bd57",
        'bg_gradient_left': "#37764a",
        'bg_gradient_right': "#0c9186"
    },
    'zebra': {
        'header_gradient_left': '#212121',
        'header_gradient_right': '#24293b',
        'bg_gradient_left': '#1e2936',
        'bg_gradient_right': '#28303f'
    }
}

DEFAULT_THEME = 'zebra'

class ThemesSingleton:
    _instance = None # holds single instance

    def __new__(cls, *args, **kwargs):
        # If no instance exists, create one with the superclass' new
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, value=None):
        if not hasattr(self, '_initialized'):
            self.value = value
            self._initialized = True
        else:
            print(f"{self.__class__} is a singleton that is already initialized!")
            pass

    def get_theme_keys(self) -> list:
        return list(THEMES.keys())

    def get_theme(self, key=None, default_value='zebra') -> dict:
        return THEMES[key] if key else THEMES[default_value]
    
    def get_default_theme_name(self) -> str:
        return DEFAULT_THEME

# Abstract away so it is used like a static class
Themes = ThemesSingleton()