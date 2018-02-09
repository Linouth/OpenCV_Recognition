import argparse
import cv2
from threading import Thread
import time
import logging

from imutils.video.pivideostream import PiVideoStream
from imutils.video import FPS
from picamera.array import PiRGBArray
from picamera import PiCamera

import dronelink


resolution = (800, 464)
col_lower = (10, 0, 160)
col_upper = (105, 75, 255)

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)


def show(frame):
    cv2.imshow('frame', frame)
    key = cv2.waitKey(1) & 0xff

    if key == ord('q'):
        return False
    elif key == ord('s'):
        filename = str(int(time.time())) + '.jpg'
        print('Saved frame to', filename)
        cv2.imwrite(filename, frame)

    return True

class Tracker():
    def __init__(self, col_lower, col_upper, resolution=(800, 464), render=False):
        self.col_lower = col_lower
        self.col_upper = col_upper

        self.cx_center = 0
        self.cy_center = 0

        self.resolution = resolution

        self.vs = PiVideoStream(resolution=resolution).start()
        time.sleep(1)
        self.fps = FPS()

        self.render = render
        self.running = True

    '''Start thread and fps counter'''
    def start(self):
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()

        self.fps.start()
        return self

    '''Update cx_center and cy_center using multithreading'''
    def update(self):
        while self.running:
            # Get frame from camera
            frame = self.vs.read()

            # Mask certain color range
            mask = cv2.inRange(frame, self.col_lower, self.col_upper)

            # Find contours of mask
            im2, contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            if len(contours) > 0:
                # cv2.drawContours(frame, contours, -1, 255, 3)

                # Find largest contour
                c = max(contours, key=cv2.contourArea)

                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0, 255, 0), 2)

                # Find center of largest contour
                cx = int(x+(w/2))
                cy = int(y+(h/2))
                cv2.circle(frame, (cx, cy), 7, (255, 255, 255), -1)

                # Find center relative to center of the image
                self.cx_center = int(cx - resolution[0]/2)
                self.cy_center = int(cy - resolution[1]/2)
                text = 'x: {}, y: {}'.format(self.cx_center, self.cy_center)
                cv2.putText(frame, text, (20, resolution[1]-40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            
            if self.render:
                if not show(frame):
                    break

            self.fps.update()

        pass

    '''Stop the thread and safely exit'''
    def stop(self):
        self.stopped = False
        self.vs.stop()
        self.fps.stop()

    '''Return the x and y coordinates of the tracked area relative to the center of the image'''
    def get_center(self):
        return self.cx_center, self.cy_center

    '''Return frames per second analized'''
    def get_fps(self):
        return self.fps.fps()

class tmp():
    def __init__(self):
        self.vehicle = None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Do some OpenCV magic')
    parser.add_argument('-r', '--render', action='store_true', help='enable rendering')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable debug messages')

    droneparse = parser.add_argument_group('Drone specific arguments')
    droneparse.add_argument('-c', '--connect', help='drone control disabled without connect string (e.g. /dev/ttyUSB0)')
    droneparse.add_argument('-b', '--baud', default=57600, help='baudrate for serial')
    droneparse.add_argument('--alt', default=2, help='flying altitude in meters')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Initialize vehicle if connection string is given
    link = dronelink.Link(args.connect, baud=args.baud, alt=args.alt)
    if link.vehicle:
        link.arm_and_takeoff()
        time.sleep(1)

    # Initialize and start tracker class
    tracker = Tracker(col_lower, col_upper, resolution=resolution, render=args.render)
    tracker.start()

    try:
        logging.info('Running')
        while True:
            x, y = tracker.get_center()
            # logging.info('x: {}, y: {}'.format(x, y))

            if link.vehicle:
                link.stabelize_alt(args.alt)
                link.adjust_to_coords(x, y, resolution)

    except KeyboardInterrupt:
        logging.info('Closing')
    finally:
        tracker.stop()
        logging.info('framerate: {}'.format(tracker.get_fps()))
        if link.vehicle:
            link.close()
