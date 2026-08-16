class BaseSkill:
    """
    All skills inherit from this class.
    """

    name = "base"
    description = "Base skill class"

    def can_handle(self, user_message: str) -> bool:
        """
        Return True if this skill should handle the message.
        """
        raise NotImplementedError

    def handle(self, user_message: str) -> str:
        """
        Execute the skill and return a response.
        """
        raise NotImplementedError