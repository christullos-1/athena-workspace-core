import os
import importlib
from core.skills.base_skill import BaseSkill

class SkillRegistry:
    def __init__(self):
        self.skills = []
        self.load_skills()

    def load_skills(self):
        """
        Auto-load all skills in the skills folder.
        """
        skills_dir = "core/skills"
        for file in os.listdir(skills_dir):
            if file.endswith("_skill.py") and file != "base_skill.py":
                module_name = f"core.skills.{file[:-3]}"
                module = importlib.import_module(module_name)

                # Find skill classes
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, type) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        self.skills.append(obj())

    def find_skill(self, user_message: str):
        """
        Return the first skill that can handle the message.
        """
        for skill in self.skills:
            if skill.can_handle(user_message):
                return skill
        return None