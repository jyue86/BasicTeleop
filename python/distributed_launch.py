from holoscan.core import Application, Fragment, Operator, OperatorSpec
from holoscan.conditions import PeriodicCondition
from pynput import keyboard
import numpy as np
import cv2

class CarlaKeyboardControllerOp(Operator):
    def __init__(self, fragment: Fragment, name: str):
        super().__init__(fragment, name=name)
        self._accel = 0.0
        self._steer = 0.0

    def start(self):
        self._listener = keyboard.Listener(
            on_press=lambda key: self._on_key_press(key),
        )
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def setup(self, spec: OperatorSpec):
        spec.output("accel")
        spec.output("steer")

    def compute(self, op_input, op_output, context):
        op_output.emit(self._accel, "accel")
        op_output.emit(self._steer, "steer")

    def _on_key_press(self, key):
        if key == keyboard.Key.up:
            self._accel = min(self._accel + 0.1, 1.0)
        elif key == keyboard.Key.down:
            self._accel = max(self._accel - 0.1, 0.0)
        elif key == keyboard.Key.left:
            self._steer = max(self._steer - 0.1, -1.0)
        elif key == keyboard.Key.right:
            self._steer = min(self._steer + 0.1, 1.0)


class CarlaCameraSensorOp(Operator):
    """Camera sensor operator - attaches to vehicle and outputs images."""

    def __init__(
        self,
        fragment: Fragment,
        name: str,
        host: str = "localhost",
        port: int = 2000,
        width: int = 1280,
        height: int = 720,
    ):
        self._host = host
        self._port = port
        self._width = width
        self._height = height
        self._client = None
        self._world = None
        self._vehicle = None
        self._camera = None
        self._latest_image = None
        # self._streamer = GStreamerStreamer("127.0.0.1", 5000, self._width, self._height, 30)
        super().__init__(fragment, name=name)

    def start(self):
        import carla

        # Connect to CARLA
        self._client = carla.Client(self._host, self._port)
        self._client.set_timeout(10.0)
        self._world = self._client.get_world()

        # Find the hero vehicle
        actors = self._world.get_actors().filter("vehicle.*")
        for actor in actors:
            if actor.attributes.get("role_name") == "hero":
                self._vehicle = actor
                break

        if self._vehicle is None and len(actors) > 0:
            self._vehicle = actors[0]

        if self._vehicle is None:
            raise RuntimeError("No vehicle found in CARLA. Run the spawn script first.")

        print(f"Camera sensor connected to vehicle: {self._vehicle.type_id}")

        # Create and attach camera sensor
        blueprint_library = self._world.get_blueprint_library()
        camera_bp = blueprint_library.find("sensor.camera.rgb")
        camera_bp.set_attribute("image_size_x", str(self._width))
        camera_bp.set_attribute("image_size_y", str(self._height))
        camera_bp.set_attribute("fov", "90")

        # Attach camera behind and above the vehicle (chase cam)
        camera_transform = carla.Transform(
            carla.Location(x=-8.0, z=4.0),
            carla.Rotation(pitch=-15.0)
        )
        self._camera = self._world.spawn_actor(
            camera_bp, camera_transform, attach_to=self._vehicle
        )

        # Register callback to receive camera images
        self._camera.listen(self._on_camera_image)
        print("Camera sensor attached and listening")

    def _on_camera_image(self, image):
        # Convert CARLA image to numpy array (BGRA format)
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = array.reshape((self._height, self._width, 4))
        # Convert BGRA to BGR for OpenCV and make a copy
        # (CARLA's buffer is invalidated after callback returns)
        self._latest_image = array[:, :, :3].copy()

    def stop(self):
        if self._camera is not None:
            self._camera.stop()
            self._camera.destroy()
            print("Camera sensor destroyed")

    def setup(self, spec: OperatorSpec):
        # spec.output("image")
        pass

    def compute(self, op_input, op_output, context):
        # Output the latest camera image
        if self._latest_image is not None:
            # op_output.emit(self._latest_image, "image")
            # Send frame to GStreamer streamer
            self._streamer.send_frame(self._latest_image.tobytes())


class CarlaCameraViewerOp(Operator):
    """Camera viewer operator - receives and displays images."""
    WINDOW_NAME = "CARLA Camera View"

    def __init__(self, fragment: Fragment, name: str):
        super().__init__(fragment, name=name)
        # self._stream_receiver = GStreamerReceiver(5000, True)

    def stop(self):
        # self._stream_receiver.stop()
        pass

    def setup(self, spec: OperatorSpec):
        # spec.input("image")
        # Gtk.main()
        pass

    def compute(self, op_input, op_output, context):
        # image = op_input.receive("image")
        # if image is not None:
        #     cv2.imshow(self.WINDOW_NAME, image)
        #     cv2.waitKey(1)
        pass


class RemoteWorkstationFragment(Fragment):
    def __init__(self, app, name):
        super().__init__(app, name=name)

    def compose(self):
        carla_controller = CarlaKeyboardControllerOp(self, name="carla_controller")
        # camera_viewer = CarlaCameraViewerOp(self, name="camera_viewer")

        # self.add_operator(camera_viewer)
        self.add_operator(carla_controller)

class CarlaDriveControllerOp(Operator):
    def __init__(self, fragment: Fragment, name: str, host: str = "localhost", port: int = 2000):
        self._host = host
        self._port = port
        self._vehicle = None
        self._world = None
        self._client = None
        super().__init__(fragment, name=name)

    def start(self):
        import carla
        self._client = carla.Client(self._host, self._port)
        self._client.set_timeout(10.0)
        self._world = self._client.get_world()

        # Force asynchronous mode so controls take effect immediately
        settings = self._world.get_settings()
        settings.synchronous_mode = False
        self._world.apply_settings(settings)

        # Find the vehicle we spawned (by role_name or get first vehicle)
        actors = self._world.get_actors().filter("vehicle.*")
        for actor in actors:
            if actor.attributes.get("role_name") == "hero":
                self._vehicle = actor
                break

        if self._vehicle is None and len(actors) > 0:
            self._vehicle = actors[0]

        if self._vehicle is None:
            raise RuntimeError("No vehicle found in Carla. Run the spawn script first.")

        print(f"Connected to vehicle: {self._vehicle.type_id}")

    def stop(self):
        if self._vehicle is not None:
            import carla
            self._vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))

    def setup(self, spec: OperatorSpec):
        spec.input("accel")
        spec.input("steer")

    def compute(self, op_input, op_output, context):
        import carla

        accel = op_input.receive("accel")
        steer = op_input.receive("steer")

        if self._vehicle is None:
            return

        # Apply control to the vehicle
        # accel > 0 means throttle, accel < 0 means brake
        if accel >= 0:
            throttle = accel
            brake = 0.0
        else:
            throttle = 0.0
            brake = abs(accel)

        control = carla.VehicleControl(
            throttle=float(throttle),
            steer=float(steer),
            brake=float(brake),
            hand_brake=False,
            reverse=False,
        )
        self._vehicle.apply_control(control)
        # self._world.tick()  # Force simulation to process the control
        print(f"Control: throttle={throttle:.2f}, steer={steer:.2f}, brake={brake:.2f}")

class KiaDriveControllerOp(Operator):
    def __init__(self, fragment: Fragment, name: str):
        super().__init__(fragment, name=name)

    def setup(self, spec: OperatorSpec):
        spec.input("accel")
        spec.input("steer")

    def compute(self, op_input, op_output, context):
        accel = op_input.receive("accel")
        steer = op_input.receive("steer")
        print(f"Kia Control: accel={accel:.2f}, steer={steer:.2f}")

class VehicleFragment(Fragment):
    def __init__(self, app, name, carla_host="localhost", carla_port=2000):
        self._carla_host = carla_host
        self._carla_port = carla_port
        super().__init__(app, name=name)

    def compose(self):
        drive_controller = CarlaDriveControllerOp(
            self,
            name="drive_controller",
            host=self._carla_host,
            port=self._carla_port,
        )
        # camera_sensor = CarlaCameraSensorOp(
        #     self,
        #     name="camera_sensor",
        #     host=self._carla_host,
        #     port=self._carla_port,
        # )
        # Ensure camera sensor emits at ~30 FPS
        # camera_sensor.add_arg(PeriodicCondition(self, recess_period=0.033))
        self.add_operator(drive_controller)
        # self.add_operator(camera_sensor)

class TeleopApp(Application):
    def __init__(self, carla_host="localhost", carla_port=2000):
        self._carla_host = carla_host
        self._carla_port = carla_port
        super().__init__()

    def compose(self):
        remote_fragment = RemoteWorkstationFragment(
            self,
            name="RemoteWorkstationFragment",
        )
        vehicle_fragment = VehicleFragment(
            self,
            name="VehicleFragment",
            carla_host=self._carla_host,
            carla_port=self._carla_port,
        )

        self.add_fragment(remote_fragment)
        self.add_fragment(vehicle_fragment)

        # Connect keyboard controller outputs to drive controller inputs
        self.add_flow(
            remote_fragment,
            vehicle_fragment,
            {("carla_controller.accel", "drive_controller.accel"),
             ("carla_controller.steer", "drive_controller.steer")},
        )


def main():
    app = TeleopApp()
    app.run()


if __name__ == "__main__":
    main()