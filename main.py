import argparse
import imutils
import cv2
import time
import sys


# min_area = 200
# area_range = (6.5, 8.5)
area_range = (13, 18)

debug = False
out = None


def show(im, win='img', wait=0):
    cv2.imshow(win, im)
    key = cv2.waitKey(wait) & 0xFF

    if key == ord('s'):
        # Save this frame
        cv2.imwrite('saves/' + str(int(time.time())) + '.jpg', im)
        print('frame saved.')
    elif key == ord('q'):
        sys.exit(0)


class Contour:
    def __init__(self, c, h):
        self.c = c
        self.h = h

        self.child = h[2]
        self.parent = h[3]

    def hasVertices(self, vertices):
        peri = cv2.arcLength(self.c, True)
        approx = cv2.approxPolyDP(self.c, 0.05 * peri, True)

        if len(approx) == vertices:
            return True
        return False

    def hasChild(self):
        if self.h[2] < 0:
            return False
        return True

    def hasParent(self):
        if self.h[3] < 0:
            return False
        return True

    def getArea(self):
        return cv2.contourArea(self.c)

    def draw(self, frame, col=(255, 255, 255)):
        return cv2.drawContours(frame, [self.c], -1, col, 2)

    def getCenter(self):
        M = cv2.moments(self.c)
        cX = int(M['m10'] / M['m00'])
        cY = int(M['m01'] / M['m00'])

        return cX, cY

    @staticmethod
    def findContours(image, mode=cv2.RETR_TREE, apprx=cv2.CHAIN_APPROX_SIMPLE):
        __, cnts, hierarchy = cv2.findContours(image, mode, apprx)
        comps = zip(cnts, hierarchy[0])
        return [Contour(comp[0], comp[1]) for comp in comps]


def findBeacon(cnts):
    for cnt in cnts:
        if cnt.hasVertices(3) and not cnt.hasChild() and cnt.hasParent():
            area_triangle = cnt.getArea()

            area_outer = 0
            parent = cnt
            while not (area_range[0] < (area_outer/area_triangle) < area_range[1]) and parent.hasParent():
                # parent = findNextShape(parent, comps)
                parent = cnts[parent.parent]
                if not parent:
                    break

                area_outer = parent.getArea()
                # print(area_outer/area_triangle)

            if area_range[0] < (area_outer/area_triangle) < area_range[1]:
                return parent
    return None


def checkFrame(frame):
    frame = imutils.resize(frame, width=400)

    height, width, channels = frame.shape
    centerX = int(width/2)
    centerY = int(height/2)

    blur = cv2.GaussianBlur(frame, (9, 9), 0)
    grey = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)

    mask = cv2.Canny(grey, 20, 70)
    if debug:
        show(mask)

    mask = cv2.dilate(mask, None, iterations=2)
    mask = cv2.erode(mask, None, iterations=1)
    if debug:
        show(mask)

    cnts = Contour.findContours(mask)
    beacon = findBeacon(cnts)

    if beacon:
        beacon.draw(frame, col=(0, 255, 0))

        cX, cY = beacon.getCenter()
        cv2.circle(frame, (cX, cY), 7, (255, 255, 255), -1)

        text = ''
        if cY < centerY:
            # Above center
            text += 'Top '
        else:
            # Below center
            text += 'Bottom '

        if cX < centerX:
            # Left of center
            text += 'Left.'
        else:
            # Right of center
            text += 'Right.'

        cv2.putText(frame, text, (20, height-40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    else:
        # print('NONE')
        # show(frame)
        # show(mask)
        # for cnt in cnts:
        #     cv2.drawContours(frame, [cnt], -1, (255, 0, 0), 1)
        #     show(frame)
        return frame, -1
    return frame, 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '--debug', action='store_true',
                    help='enable some debugging information')
    ap.add_argument('-o', '--outvid', help='output file for video')
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--image', help='path to a image file')
    group.add_argument('-v', '--video', help='path to a video file')
    group.add_argument('-p', '--picam', action='store_true',
                       help='raspberry pi camera module')
    group.add_argument('-c', '--webcam', dest='video', type=int,
                       help='camera interface number')
    args = vars(ap.parse_args())

    debug = args['debug']

    if args.get('outvid'):
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        # out = cv2.VideoWriter(args['outvid'], fourcc, 30.0, (1280, 720))
        # out = cv2.VideoWriter(args['outvid'], fourcc, 30.0, (800, 450))
        out = cv2.VideoWriter(args['outvid'], fourcc, 30.0, (400, 300))
        print('activate')

    if args.get('image'):
        im = cv2.imread(args['image'])
        im, state = checkFrame(im)

        show(im)
    elif args.get('video') != None:
        frame_count = 0
        frame_error_count = 0
        cap = cv2.VideoCapture(args['video'])

        # Loop through vid
        while (cap.isOpened()):
            ret, im = cap.read()
            if not ret:
                break

            im, state = checkFrame(im)
            if out:
                out.write(im)

            if debug:
                show(im)
            else:
                show(im, wait=1)

            frame_count += 1
            if state < 0:
                frame_error_count += 1

        cap.release()
        print('Total played frames: {}'.format(frame_count))
        print('Frames without beacon: {}'.format(frame_error_count))
        print('Percentage OK: {}%'
              .format(((frame_count-frame_error_count)/frame_count)*100))
    elif args.get('picam'):
        from picamera.array import PiRGBArray
        from picamera import PiCamera
        from imutils.video.pivideostream import PiVideoStream
        from imutils.video import FPS

        vs = PiVideoStream(resolution=(800,464)).start()
        time.sleep(2)
        fps = FPS().start()

        i = 0
        while True or i < 200:
            i += 1
            frame = vs.read()
            frame = imutils.resize(frame, width=800)

            #im, state = checkFrame(frame)

            #show(im, wait=1)
            cv2.imshow('frame', frame)
            key = cv2.waitKey(1) & 0xff

            if key == ord('q'):
                break

            print(i)


            fps.update()

        fps.stop()
        vs.stop()

        print('Framerate', fps.fps())

        '''
        #res = (1280, 720)
        res = (800, 450)
        camera = PiCamera()
        camera.resolution = res
        camera.framerate = 30
        rawCapture = PiRGBArray(camera, size=res)

        time.sleep(0.1)
        i = 0

        for frame in camera.capture_continuous(rawCapture, format='bgr', use_video_port=True):
                i += 1
                image = frame.array

                cv2.imshow('Frame', image)
                key = cv2.waitKey(1) & 0xff

                rawCapture.truncate(0)

                if key == ord('q'):
                    break
                print('FRAME', i)
        '''
        

    cv2.destroyAllWindows()
