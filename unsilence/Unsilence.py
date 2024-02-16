import atexit
import shutil
import sys
from os import PathLike
from pathlib import Path

from unsilence.lib.detect_silence.DetectSilence import detect_silence
from unsilence.lib.intervals.Intervals import Intervals
from unsilence.lib.intervals.TimeCalculations import calculate_time
from unsilence.lib.render_media.MediaRenderer import MediaRenderer
from unsilence.lib.tools.ffmpeg_version import is_ffmpeg_usable


class Unsilence:
    """
    Unsilence Class to remove (or isolate or many other use cases) silence from audible video parts
    """

    def __init__(self, input_file: str | PathLike, temp_dir: str | PathLike = Path(".tmp")):
        """
        :param input_file: The file that should be processed
        :type input_file: str | PathLike
        :param temp_dir: The temp dir where temporary files can be saved
        :type temp_dir: str | PathLike
        """
        self._input_file = Path(input_file)
        self._temp_dir = Path(temp_dir)
        self._intervals: Intervals | None = None

        ffmpeg_status = is_ffmpeg_usable()
        if ffmpeg_status == "not_detected":
            raise EnvironmentError("ffmpeg not found!")
        elif ffmpeg_status == "requirements_unsatisfied":
            raise EnvironmentError("ffmpeg version not supported, a version >= 4.2.4 is required!")
        elif ffmpeg_status == "unknown_version":
            print("Could not detect ffmpeg version, proceed at your own risk! (version >= 4.2.4 required)",
                  file=sys.stderr)

        atexit.register(self.cleanup)

    def detect_silence(self, **kwargs):
        """
        Detects silence of the file (Options can be specified in kwargs)

        :param `\**kwargs`: Remaining keyword arguments are passed to :func:`~unsilence.lib.detect_silence.DetectSilence.detect_silence`

        :return: A generated Intervals object
        :rtype: ~unsilence.lib.intervals.Intervals.Intervals
        """
        self._intervals = detect_silence(self._input_file, **kwargs)
        return self._intervals

    def set_intervals(self, intervals: Intervals):
        """
        Set the intervals so that they do not need to be re-detected

        :param intervals: Intervals collection
        :type intervals: ~unsilence.lib.intervals.Intervals.Intervals

        :return: None
        """
        self._intervals = intervals

    def get_intervals(self):
        """
        Get the current Intervals so they can be reused if wanted

        :return: Intervals collection
        :rtype: ~unsilence.lib.intervals.Intervals.Intervals
        """
        return self._intervals

    def get_input_file(self):
        return self._input_file

    def estimate_time(self, audible_speed: float = 1, silent_speed: float = 6):
        """
        Estimates the time (savings) when the current options are applied to the intervals

        :param audible_speed: The speed at which the audible intervals get played back at
        :type audible_speed: float
        :param silent_speed: The speed at which the silent intervals get played back at
        :type silent_speed: float

        :raises: **ValueError** -- If silence detection was never run

        :return: Dictionary of time information
        :rtype: dict
        """
        if self._intervals is None:
            raise ValueError("Silence detection was not yet run and no intervals where given manually!")

        return calculate_time(self._intervals, audible_speed, silent_speed)

    def render_media(self, output_file: str | PathLike, **kwargs):
        """
        Renders the current intervals with options specified in the kwargs

        :param output_file: Where the final file should be saved at
        :type output_file: str | PathLike
        :param `\**kwargs`: Remaining keyword arguments are passed to :func:`~unsilence.lib.render_media.MediaRenderer.MediaRenderer.render`
       
        :return: None
        """
        if self._intervals is None:
            raise ValueError("Silence detection was not yet run and no intervals where given manually!")

        renderer = MediaRenderer(self._temp_dir)
        renderer.render(self._input_file, output_file, self._intervals, **kwargs)

    def cleanup(self):
        """
        Cleans up the temporary directories, called automatically when the program ends

        :return: None
        """
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
