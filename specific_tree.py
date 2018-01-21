import argparse
import imutils
import cv2


min_area = 100
colLower = (160, 60, 60)
colUpper = (180, 255, 255)


ap = argparse.ArgumentParser()
ap.add_argument('-i', '--image', required=True, help='path to the image file')
args = vars(ap.parse_args())

image = cv2.imread(args['image'])
image = imutils.resize(image, width=800)

height, width, channels = image.shape
centerX = int(width/2)
centerY = int(height/2)

# image = cv2.GaussianBlur(image, (5, 5), 0)
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, colLower, colUpper)
mask = cv2.dilate(mask, None, iterations=8)
mask = cv2.erode(mask, None, iterations=8)
cv2.imshow('img', mask)
cv2.waitKey(0)

__, cnts, hierarchy = cv2.findContours(mask, cv2.RETR_TREE,
                                       cv2.CHAIN_APPROX_SIMPLE)

# TMP
cv2.circle(image, (centerX, centerY), 10, (255, 255, 255), -1)

outera = 0
innera = 0

for comp in zip(cnts, hierarchy[0]):
    c = comp[0]
    h = comp[1]

    area = cv2.contourArea(c)
    if area < min_area:
        # Area too small
        continue

    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.04 * peri, True)

    if h[2] < 0:
        # Innermost
        col = (255, 0, 0)
        print('Inner area: {}'.format(area))
        innera = area
    elif h[3] < 0:
        # Outermost
        col = (0, 255, 0)
        print('Outer area: {}'.format(area))
        outera = area
    else:
        # Somewhere inbetween
        col = (0, 0, 255)
        print('Between area: {}'.format(area))

    print('Vertices: {}'.format(len(approx)))
    # if len(approx) != 3:
    if len(approx) < 3 or len(approx) > 4:
        continue

    M = cv2.moments(c)
    try:
        cX = int(M['m10'] / M['m00'])
        cY = int(M['m01'] / M['m00'])
    except ZeroDivisionError:
        print('ZeroDivide')

    cv2.drawContours(image, [c], -1, col, 2)
    cv2.circle(image, (cX, cY), 7, (255, 255, 255), -1)
    cv2.putText(image, 'center', (cX - 20, cY - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

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

    cv2.putText(image, text, (20, height-40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

cv2.imshow('img', image)
cv2.waitKey(0)

print('Outer/Inner: {}'.format(outera/innera))

cv2.destroyAllWindows()
