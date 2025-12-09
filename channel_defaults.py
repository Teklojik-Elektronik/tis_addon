# Default channel names for TIS appliance types
# Based on DefaultApplianceChannelsSeeder.php from Laravel addon

DEFAULT_CHANNEL_NAMES = {
    "switch": {
        1: "Output Channel"
    },
    "dimmer": {
        1: "Output Channel"
    },
    "rgbw": {
        1: "Red Channel",
        2: "Green Channel", 
        3: "Blue Channel",
        4: "White Channel"
    },
    "rgb": {
        1: "Red Channel",
        2: "Green Channel",
        3: "Blue Channel"
    },
    "ac": {
        1: "AC"
    },
    "floor_heating": {
        1: "Floor Heating"
    },
    "shutter": {
        1: "Up Channel",
        2: "Down Channel"
    },
    "motor": {
        1: "Output Channel"
    },
    "binary_sensor": {
        1: "Input Channel"
    },
    "security": {
        1: "Input Channel"
    },
    "analog_sensor": {
        1: "Input Channel"
    },
    "energy_sensor": {
        1: "Input Channel"
    },
    "universal_switch": {
        1: "Input Channel"
    },
    "health_sensor": {
        1: "Input Channel"
    },
    "lux_sensor": {
        1: "Input Channel"
    },
    "temperature_sensor": {
        1: "Input Channel"
    }
}


def get_default_channel_name(appliance_type: str, channel_number: int, total_channels: int = 1) -> str:
    """Get default channel name based on appliance type and channel number.
    
    Args:
        appliance_type: Type of appliance (e.g., 'switch', 'rgbw', 'shutter')
        channel_number: Channel number (1-based)
        total_channels: Total number of channels for the device
        
    Returns:
        str: Default channel name
    """
    type_defaults = DEFAULT_CHANNEL_NAMES.get(appliance_type.lower(), {})
    
    # If specific channel name exists, use it
    if channel_number in type_defaults:
        return type_defaults[channel_number]
    
    # For multi-channel devices, use generic naming
    if total_channels > 1:
        return f"Channel {channel_number}"
    
    # For single channel, use appliance type
    return appliance_type.replace('_', ' ').title()
