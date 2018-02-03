import argparse
import imutils
import cv2
import time
import sys


# min_area = 200
# area_range = (6.5, 8.5)
area_range = (13, 21)

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


def hasVertices(comp, vertices):
    c = cv2.convexHull(comp[0])
    # c = comp[0]

    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.05 * peri, True)

    if len(approx) == vertices:
        return True
    return False


def hasChild(comp):
    h = comp[1]

    if h[2] < 0:
        return False
    return True


def hasParent(comp):
    h = comp[1]

    if h[3] < 0:
        return False
    return True


def findBeacon(comps):
    for comp in comps:
        if hasVertices(comp, 3) and not hasChild(comp) and hasParent(comp):
            # c = cv2.convexHull(comp[0])
            c = comp[0]
            area_triangle = cv2.contourArea(c)

            area_outer = 0
            parent = comp
            while not (area_range[0] < (area_outer/area_triangle) < area_range[1]) and hasParent(parent):
                # parent = findNextShape(parent, comps)
                parent = comps[parent[1][3]]
                if not parent:
                    break

                area_outer = cv2.contourArea(parent[0])
                # print(area_outer/area_triangle)

            if area_range[0] < (area_outer/area_triangle) < area_range[1]:
                return parent
    return None


def checkFrame(frame):
    frame = imutils.resize(frame, width=1280)

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

    __, cnts, hierarchy = cv2.findContours(mask, cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)

    try:
        comps = list(zip(cnts, hierarchy[0]))
    except TypeError:
        return 0, -1

    beacon = findBeacon(comps)
    if beacon:
        cv2.drawContours(frame, [beacon[0]], -1, (0, 255, 0), 2)
        M = cv2.moments(beacon[0])
        try:
            cX = int(M['m10'] / M['m00'])
            cY = int(M['m01'] / M['m00'])
        except ZeroDivisionError:
            print('ZeroDivide')

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
    group.add_argument('-c', '--webcam', dest='video', type=int,
                       help='camera interface number')
    args = vars(ap.parse_args())

    debug = args['debug']

    if args.get('outvid'):
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        out = cv2.VideoWriter(args['outvid'], fourcc, 30.0, (1280, 720))
        # out = cv2.VideoWriter(args['outvid'], fourcc, 30.0, (800, 450))
        print('activate')

    if args.get('image'):
        im = cv2.imread(args['image'])
        im, state = checkFrame(im)

        show(im)
    elif args.get('video'):
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
        print(f'Total played frames: {frame_count}')
        print(f'Frames without beacon: {frame_error_count}')
        print('Percentage OK: {}%'
              .format(((frame_count-frame_error_count)/frame_count)*100))

    cv2.destroyAllWindows()
