import logging
from dronekit import connect, VehicleMode
from pymavlink import mavutil
import time


logger = logging.getLogger()


class Link():
    def __init__(self, connect_string, baud=57600, alt=None):
        self.vehicle = connect(connect_string, baud=baud, wait_ready=True) if connect_string else None
        self.alt = alt

    def arm_and_takeoff(self, alt=None):
        altitude = self.alt or alt
        if not altitude:
            logger.critical('No altitude given to takeoff')
            return -1

        while not self.vehicle.is_armable:
            logger.debug('Waiting for vehicle to initialize')
            time.sleep(1)

        logger.info('Arming')
        self.vehicle.mode = VehicleMode('GUIDED_NOGPS')
        self.vehicle.armed = True

        while not self.vehicle.armed:
            logger.debug('Waiting for arming')
            time.sleep(1)

        logger.debug('Taking off')
        self.vehicle.simple_takeoff(altitude)

        while True:
            if self.vehicle.location.global_relative_frame.alt >= altitude*0.95:
                logger.info('Altitude reached!')
                break

    def stabelize_alt(self, alt=None):
        # TODO: Clean this up.
        new_alt = alt or self.alt
        if not new_alt:
            logger.critical('No altitude given for stabilization')
            return -1

        drone_alt = self.vehicle.location.global_relative_frame.alt
        while True:
            if (self.vehicle.location.global_relative_frame.alt >= new_alt*0.95 or
                    self.vehicle.location.global_relative_frame.alt <= new_alt*1.1):
                logger.info('Altitude {} reached.'.format(new_alt))
                break

    def adjust_to_coords(self, x, y, res):
        vx = x/(res[0]/2)
        vy = y/(res[1]/2)

        logger.debug('Moving to ({}, {}) with velocity ({}, {})'.format(x, y, vx, vy))
        # self._set_velocity_body(vx, vy, 0)

    def close(self):
        self.vehicle.mode = VehicleMode('LAND')
        self.vehicle.close()

    def _set_velocity_body(self, vx, vy, vz):
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                0,
                0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,  #-- BITMASK -> Consider only the velocities
                0, 0, 0,             #-- POSITION
                vx, vy, vz,          #-- VELOCITY
                0, 0, 0,             #-- ACCELERATIONS
                0, 0)
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()

    def _set_attitude(self, thrust = 0.5, duration = 0):
        # Thrust >  0.5: Ascend
        # Thrust == 0.5: Hold the altitude
        # Thrust <  0.5: Descend
        msg = vehicle.message_factory.set_attitude_target_encode(
            0, # time_boot_ms
            1, # Target system
            1, # Target component
            0b00000000, # Type mask: bit 1 is LSB
            [1.0, 0.0, 0.0, 0.0], # Quaternion
            0, # Body roll rate in radian
            0, # Body pitch rate in radian
            0, # Body yaw rate in radian
            thrust  # Thrust
        )
        self.vehicle.send_mavlink(msg)

        start = time.time()
        while time.time() - start < duration:
            self.vehicle.send_mavlink(msg)
            time.sleep(0.1)




