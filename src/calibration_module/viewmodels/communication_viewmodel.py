from PySide6.QtCore import QObject, Signal
import os
import ping3
from services.service_locator import ServiceLocator
import platform
from PySide6.QtCore import QTimer
import subprocess


class CommunicationSetupViewModel(QObject):
    # Signals for View updates
    connection_status_changed = Signal(str, str)  # (status_text, color)
    dli_status_changed = Signal(str, str)  # (status_text, color)
    import_button_enabled_changed = Signal(bool)
    testing_state_changed = Signal(bool)  # For enabling/disabling test button

    def __init__(self):
        super().__init__()
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )
        self.current_version = ""
        self.is_testing = False
        self.target_ip = self.settings_service.get_setting("app.carto_ip")

    def get_target_ip(self):
        return self.target_ip

    def test_connection(self):
        self.testing_state_changed.emit(True)
        self.connection_status_changed.emit("Testing...", "black")

        # Use QTimer to avoid blocking UI
        QTimer.singleShot(100, self._perform_connection_test)

    def _perform_connection_test(self):
        try:
            is_connected = self.check_connection()

            if is_connected:
                self.connection_status_changed.emit("Connected", "green")
            else:
                self.connection_status_changed.emit("Connection Failed", "red")
        finally:
            self.testing_state_changed.emit(False)

    def check_connection(self) -> bool:
        try:
            ip = self.get_target_ip()
            print(f"Checking connection to {ip}...")

            if platform.system() == "Windows":
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
            else:
                # macOS uses different flags
                cmd = ["ping", "-c", "1", "-W", "1", ip]

            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.lower()
            print(f"Ping output: {output}")

            # Platform-specific output parsing
            if platform.system() == "Windows":
                # Windows-specific checks
                if "destination host unreachable" in output:
                    print("Status: Host unreachable")
                    return False
                if "request timed out" in output:
                    print("Status: Request timed out")
                    return False
                if "could not find host" in output:
                    print("Status: Host not found")
                    return False

                # Windows success pattern
                if "bytes=32" in output and "time=" in output:
                    try:
                        time_start = output.find("time=") + 5
                        time_end = output.find("ms", time_start)
                        if time_end > time_start:
                            time_ms = float(output[time_start:time_end])
                            print(f"Response time: {time_ms}ms")
                            return time_ms < 1000
                    except ValueError:
                        print("Status: Invalid response time format")
                        return False

            else:
                # macOS-specific checks
                if "no route to host" in output:
                    print("Status: No route to host")
                    return False
                if "request timeout" in output:
                    print("Status: Request timed out")
                    return False
                if "unknown host" in output:
                    print("Status: Unknown host")
                    return False

                # macOS success pattern
                if "bytes from" in output and "time=" in output:
                    try:
                        # macOS format: "time=2.064 ms"
                        time_start = output.find("time=") + 5
                        time_end = output.find("ms", time_start)
                        if time_end > time_start:
                            time_ms = float(output[time_start:time_end])
                            print(f"Response time: {time_ms}ms")
                            return time_ms < 1000
                    except ValueError:
                        print("Status: Invalid response time format")
                        return False

            print("Status: No valid response detected")
            return False

        except Exception as e:
            print(f"Connection check error: {str(e)}")
            return False

    def validate_version(self, version: str):
        self.current_version = version.strip()

        if not self.current_version:
            self.dli_status_changed.emit("Enter CARTO version", "black")
            self.import_button_enabled_changed.emit(False)
            return

        has_dli = self.check_dli_version(self.current_version)
        if has_dli:
            self.dli_status_changed.emit(
                f"DLI v{self.current_version} available", "green"
            )
            self.import_button_enabled_changed.emit(False)
        else:
            self.dli_status_changed.emit(
                f"DLI v{self.current_version} not found", "red"
            )
            self.import_button_enabled_changed.emit(True)

    def handle_dli_import(self, dll_path: str):
        if not dll_path or not self.current_version:
            return False

        success = self.import_dli_files(self.current_version, dll_path)

        if success:
            self.dli_status_changed.emit(
                f"DLI v{self.current_version} imported successfully", "green"
            )
            self.import_button_enabled_changed.emit(False)
        else:
            self.dli_status_changed.emit("Import failed", "red")
            self.import_button_enabled_changed.emit(True)

        return success
