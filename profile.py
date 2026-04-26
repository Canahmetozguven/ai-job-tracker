"""Profile loader module."""

def load_profile(path: str) -> str:
    """Load user profile from text file.

    Args:
        path: Path to profile.txt file

    Returns:
        Profile text string

    Raises:
        FileNotFoundError: If profile file doesn't exist
    """
    with open(path) as f:
        return f.read().strip()