def arm_and_takeoff(connect, alt, baud=57600):
    vehicle = connect(args.connect, baud=57600, wait_ready=True)

    while not vehicle.is_armable:
        print('Waiting for vehicle to initialize')
        time.sleep(1)

    print('Arming')
    vehicle.mode = VehicleMode('GUIDED')
    vehicle.armed = True

    while not vehicle.armed:
        print('Waiting for arming')
        time.sleep(1)

    print('Taking off')
    vehicle.simple_takeoff(altitude)

    print('Alt:', vehicle.location.global_relative_frame.alt)
    if vehicle.location.global_relative_frame.alt >= altitude*0.95:
        print('Altitude reached!')
        break
