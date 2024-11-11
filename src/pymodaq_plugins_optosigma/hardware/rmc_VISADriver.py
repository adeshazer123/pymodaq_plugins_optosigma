import pyvisa
import time
import logging

logger = logging.getLogger(__name__)


class AxisError(Exception):
    MESSAGES = {
        "K": "Normal state",
        "A": "Other",
        "O": "Overflow"
    }

    def __init__(self, error_code):
        self.message = self.MESSAGES[error_code]


class RMCVISADriver:
    """Class to communicate with the RMC Actuator"""

    default_units = "um"

    def __init__(self, rsrc_name):
        self._actuator = None
        self.rsrc_name = rsrc_name
        self.position = [None, None]
        self.speed = [None, None]

    def check_error(self):
        error = self._actuator.query("Q:")
        error = error.split(",")[2]
        if error != "K":
            logger.error(f"Error: {error}")
            AxisError(error)

    def set_speed(self, speed, channel):
        if 0 < speed <= 8:
            speed = self._actuator.write(f"D:{channel}J{speed}")
            self.speed[channel - 1] = speed
        else:
            Exception("Invalid speed values")

    def get_speed(self, channel):
        """Returns the speed of the specified channel."""
        return self.speed[channel - 1]

    def connect(self):
        try:
            rm = pyvisa.ResourceManager()
            self._actuator = rm.open_resource(self.rsrc_name)
            self._actuator.write_termination = "\r\n"
            self._actuator.read_termination = "\r\n"
            logger.info(f"Connection to {self._actuator} successful")
        except Exception as e:
            logger.error(f"Error connecting to {self.rsrc_name}: {e}")

    def set_mode(self):
        self._actuator.write("P:1")  # Manual mode disabeled

    def move(self, position, channel):
        """Move the actuator to the specified position on the given channel.
        Parameters
        ----------
        position: int
            The position to move to.
        channel: int
            The channel to move.

        """
        self.wait_for_ready(channel)
        if position >= 0:
            self._actuator.write(f"A:{channel}+U{position}")

        else:
            self._actuator.write(f"A:{channel}-U{abs(position)}")
        self._actuator.write("G:")
        self.wait_for_ready(channel)
        self.position[channel - 1] = position

    def get_position(self, channel):
        """Returns the position of the specified channel."""
        # position = self._actuator.query(f"Q:")
        # while position[0] != "+" or position[0] != "-":
        #     position = self._actuator.query(f"Q:")
        #
        # position = int(position.split(",")[channel-1].replace(" ",""))

        return self.position[channel - 1]

    def move_relative(self, position, channel):
        self.wait_for_ready(channel)
        if position >= 0:
            self._actuator.write(f"M:{channel}+U{position}")
            logger.info(f"Moving {channel} to {position}")
        else:
            self._actuator.write(f"M:{channel}-U{abs(position)}")
            logger.info(f"Moving {channel} to {position}")
        self._actuator.write("G:")  # check if this is correct
        self.wait_for_ready(channel)
        self.position[channel - 1] = position + self.position[channel - 1]

    def home(self, channel):
        self.wait_for_ready(channel)
        self._actuator.write(f"H:{channel}")
        logger.info(f"Homing {channel}")
        self.wait_for_ready(channel)
        self.position[channel - 1] = 0

    def wait_for_ready(self, channel):
        time0 = time.time()
        while self.read_state(channel) != "R":
            logger.info("State: " + self.read_state(channel))
            time1 = time.time() - time0
            if time1 >= 60:
                logger.warning("Timeout")
                self.check_error(channel)
                break
            time.sleep(0.2)

    def stop(self, channel):
        """Stop the actuator on the specified channel."""
        self._actuator.write(f"L:{channel}")
        logger.info(f"Actuator {channel} stopped")
        self.wait_for_ready(channel)

    def read_state(self, channel):
        """Returns the state of the specified channel."""
        state = self._actuator.query("!:")
        state = state.split(",")[channel - 1]
        return state

    def close(self):
        pyvisa.ResourceManager().close()
