from metagpt.actions import (
    UserRequirement,
    WriteDesign,
    WritePRD,
    WriteTasks,
    WriteTest,
)
from metagpt.actions.summarize_code import SummarizeCode
from metagpt.environment.base_env import Environment
from metagpt.logs import get_human_input
from metagpt.roles import (
    Architect,
    Engineer,
    ProductManager,
    ProjectManager,
    QaEngineer,
    Role,
)
from metagpt.schema import Message
from metagpt.utils.common import any_to_str, any_to_str_set


class MGXEnv(Environment):
    """MGX Environment"""

    def _publish_message(self, message: Message, peekable: bool = True) -> bool:
        return super().publish_message(message, peekable)

    def publish_message(self, message: Message, user_defined_recipient: str = "", publicer: str = "") -> bool:
        """let the team leader take over message publishing"""
        tl = self.get_role("Team Leader")

        if user_defined_recipient:
            self._publish_message(message)
            # bypass team leader, team leader only needs to know but not to react
            tl.rc.memory.add(self.move_message_info_to_content(message))

        elif self.message_within_software_sop(message) and not self.has_user_requirement():
            # Quick routing for messages within software SOP, bypassing TL.
            # Use rules to check for user intervention and to finish task.
            # NOTE: This escapes TL's supervision and has pitfalls such as routing obsolete messages even if TL has acquired a new user requirement.
            #       In addition, we should not determine the status of a task based on message cause_by.
            #       Consider replacing this in the future.
            self._publish_message(message)
            if self.is_software_task_finished(message):
                tl.rc.memory.add(self.move_message_info_to_content(message))
                tl.finish_current_task()

        elif publicer == tl.profile:
            # message processed by team leader can be published now
            self._publish_message(message)

        else:
            # every regular message goes through team leader
            message = self.move_message_info_to_content(message)
            message.send_to.add(tl.name)
            tl.put_message(message)

        self.history.add(message)

        return True

    async def ask_human(self, question: str, sent_from: Role = None) -> str:
        # NOTE: Can be overwritten in remote setting
        return await get_human_input(question)

    async def reply_to_human(self, content: str, sent_from: Role = None) -> str:
        # NOTE: Can be overwritten in remote setting
        return content

    def message_within_software_sop(self, message: Message) -> bool:
        return message.sent_from in any_to_str_set([ProductManager, Architect, ProjectManager, Engineer, QaEngineer])

    def has_user_requirement(self, k=2) -> bool:
        """A heuristics to check if there is a recent user intervention"""
        return any_to_str(UserRequirement) in [msg.cause_by for msg in self.history.get(k)]

    def is_software_task_finished(self, message: Message) -> bool:
        """Use a hard-coded rule to check if one software task is finished"""
        return message.cause_by in any_to_str_set([WritePRD, WriteDesign, WriteTasks, SummarizeCode]) or (
            message.cause_by == any_to_str(WriteTest) and "Exceeding" in message.content
        )

    def move_message_info_to_content(self, message: Message) -> Message:
        """Two things here:
        1. Convert role, since role field must be reserved for LLM API, and is limited to, for example, one of ["user", "assistant", "system"]
        2. Add sender and recipient info to content, making TL aware, since LLM API only takes content as input
        """
        if message.role in ["system", "user", "assistant"]:
            sent_from = message.sent_from
        else:
            sent_from = message.role
            message.role = "assistant"
        message.content = f"from {sent_from} to {message.send_to}: {message.content}"
        return message
