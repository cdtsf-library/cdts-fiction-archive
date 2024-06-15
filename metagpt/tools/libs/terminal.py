import subprocess
import threading
from queue import Queue

from metagpt.tools.tool_registry import register_tool
from metagpt.utils.report import END_MARKER_VALUE, TerminalReporter


@register_tool()
class Terminal:
    """
    A tool for running terminal commands.
    Don't initialize a new instance of this class if one already exists.
    For commands that need to be executed within a Conda environment, it is recommended
    to use the `execute_in_conda_env` method.
    """

    def __init__(self):
        self.shell_command = ["bash"]  # FIXME: should consider windows support later
        self.command_terminator = "\n"

        # Start a persistent shell process
        self.process = subprocess.Popen(
            self.shell_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            executable="/bin/bash",
        )
        self.stdout_queue = Queue()
        self.observer = TerminalReporter()

        self._check_state()

    def _check_state(self):
        """Check the state of the terminal, e.g. the current directory of the terminal process. Useful for agent to understand."""
        print("The terminal is at:", self.run_command("pwd"))

    def run_command(self, cmd: str, daemon=False) -> str:
        """
        Executes a specified command in the terminal and streams the output back in real time.
        This command maintains state across executions, such as the current directory,
        allowing for sequential commands to be contextually aware. The output from the
        command execution is placed into `stdout_queue`, which can be consumed as needed.

        Args:
            cmd (str): The command to execute in the terminal.
            daemon (bool): If True, executes the command in a background thread, allowing
                           the main program to continue execution. The command's output is
                           collected asynchronously in daemon mode and placed into `stdout_queue`.

        Returns:
            str: The command's output or an empty string if `daemon` is True. Remember that
                 when `daemon` is True, the output is collected into `stdout_queue` and must
                 be consumed from there.

        Note:
            If `stdout_queue` is not periodically consumed, it could potentially grow indefinitely,
            consuming memory. Ensure that there's a mechanism in place to consume this queue,
            especially during long-running or output-heavy command executions.
        """

        # Send the command
        self.process.stdin.write((cmd + self.command_terminator).encode())
        self.process.stdin.write(
            (f'echo "{END_MARKER_VALUE}"{self.command_terminator}').encode()  # write EOF
        )  # Unique marker to signal command end
        self.process.stdin.flush()
        if daemon:
            threading.Thread(target=self._read_and_process_output, args=(cmd,), daemon=True).start()
            return ""
        else:
            return self._read_and_process_output(cmd)

    def execute_in_conda_env(self, cmd: str, env, daemon=False) -> str:
        """
        Executes a given command within a specified Conda environment automatically without
        the need for manual activation. Users just need to provide the name of the Conda
        environment and the command to execute.

        Args:
            cmd (str): The command to execute within the Conda environment.
            env (str, optional): The name of the Conda environment to activate before executing the command.
                                 If not specified, the command will run in the current active environment.
            daemon (bool): If True, the command is run in a background thread, similar to `run_command`,
                           affecting error logging and handling in the same manner.

        Returns:
            str: The command's output, or an empty string if `daemon` is True, with output processed
                 asynchronously in that case.

        Note:
            This function wraps `run_command`, prepending the necessary Conda activation commands
            to ensure the specified environment is active for the command's execution.
        """
        cmd = f"conda run -n {env} {cmd}"
        return self.run_command(cmd, daemon=daemon)

    def _read_and_process_output(self, cmd):
        with self.observer as observer:
            cmd_output = []
            observer.report(cmd + self.command_terminator, "cmd")
            # report the comman
            # Read the output until the unique marker is found.
            # We read bytes directly from stdout instead of text because when reading text,
            # '\r' is changed to '\n', resulting in excessive output.
            tmp = b""
            while True:
                output = tmp + self.process.stdout.read(1)
                *lines, tmp = output.splitlines(True)
                for line in lines:
                    line = line.decode()
                    ix = line.rfind(END_MARKER_VALUE)
                    if ix >= 0:
                        line = line[0:ix]
                        if line:
                            observer.report(line, "output")
                            # report stdout in real-time
                            cmd_output.append(line)
                        return "".join(cmd_output)
                    # log stdout in real-time
                    observer.report(line, "output")
                    cmd_output.append(line)
                    self.stdout_queue.put(line)

    def close(self):
        """Close the persistent shell process."""
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait()
