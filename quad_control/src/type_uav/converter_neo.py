#!/usr/bin/env python
# this line is just used to define the type of document
 
'''
    Purpose: converts a desired force (in NEWTONS) to IRIS+ standard

    throttle_neutral is the most critical parameter, that needs to be reseted when an experiment is commenced

'''

import numpy
import rospy
import utilities.utility_functions as uts



class IrisPlusConverter(object):

    # acceleration due to gravity (m/s/s)
    __GRAVITY = rospy.get_param("gravity_ctr",9.81)


    # The default of 4.5 commands a 200 deg/sec rate
    # of rotation when the yaw stick is held fully left or right.
    MAX_PSI_SPEED_Deg = 200.0 

    MAX_ANGLE_DEG = 45.0 

    def __init__(self,
    throttle_neutral = rospy.get_param("throttle_neutral",1.0),
    total_mass = rospy.get_param("total_mass",1.0)
    ):

        self.force_median = uts.MedianFilter3D(70)
        
        # # Throttle neutral 
        # self.throttle_neutral = throttle_neutral
        # self.roll_neutral  = 1500
        # self.pitch_neutral = 1500

        # Throttle neutral 
        self.throttle_neutral = throttle_neutral
        self.roll_neutral  = rospy.get_param("roll_neutral_value",0.0)
        self.pitch_neutral = rospy.get_param("pitch_neutral_value",0.0)

        # total mass
        self.total_mass = total_mass

        # in RADIANS
        self.euler_angles = numpy.array([0.0,0.0,0.0])
        # rotation matrix initialization
        self.rotation_matrix = numpy.identity(3)

        self.roll_compensation = rospy.get_param("neo_roll_gain",1.0)
        self.pitch_compensation = rospy.get_param("neo_pitch_gain",1.0)

        if rospy.get_param("complete_neutral_reset",False):
            self.reset_k_trottle_neutral = self.complete_reset_k_trottle_neutral
        else:
            self.reset_k_trottle_neutral = self.incomplete_reset_k_trottle_neutral

    def set_mass(self,mass):
        self.total_mass = mass
        pass

    def get_k_throttle_neutral(self):
        return self.throttle_neutral

    def incomplete_reset_k_trottle_neutral(self):
        # if force > m*gravity, decrease neutral value
        # if force < m*gravity, increase neutral value

        median_force = self.force_median.output()

        median_force_z = median_force[2]
        rospy.logwarn('median force = '+ str(median_force_z))

        self.throttle_neutral = self.throttle_neutral*median_force_z/(self.total_mass*self.__GRAVITY)

        # for safety better bound this value
        self.throttle_neutral = numpy.clip(self.throttle_neutral,1350,1600)
        rospy.logwarn('new neutral value = ' + str(self.throttle_neutral) + ' in [1350,1600]')

        return

    def complete_reset_k_trottle_neutral(self):
        # if force > m*gravity, decrease neutral value
        # if force < m*gravity, increase neutral value

        median_force = self.force_median.output()

        median_force_z = median_force[2]
        rospy.logwarn('median force = '+ str(median_force_z))

        self.throttle_neutral = self.throttle_neutral*median_force_z/(self.total_mass*self.__GRAVITY)

        # for safety better bound this value
        self.throttle_neutral = numpy.clip(self.throttle_neutral,1350,1600)
        rospy.logwarn('new neutral value = ' + str(self.throttle_neutral) + ' in [1350,1600]')


        roll_desired_median,pitch_desired_median = self.roll_pitch(median_force)

        MAX_PSI_SPEED_Deg = self.MAX_PSI_SPEED_Deg
        MAX_PSI_SPEED_Rad = MAX_PSI_SPEED_Deg*numpy.pi/180.0

        MAX_ANGLE_DEG = self.MAX_ANGLE_DEG
        MAX_ANGLE_RAD = MAX_ANGLE_DEG*numpy.pi/180.0

        self.roll_neutral = self.roll_neutral + self.roll_compensation*roll_desired_median*500.0/MAX_ANGLE_RAD
        self.roll_neutral = numpy.clip(self.roll_neutral,1440,1560)
        rospy.logwarn('new roll neutral value = ' + str(self.roll_neutral) + ' in [1440,1560]')

        self.pitch_neutral =  self.pitch_neutral - self.pitch_compensation*pitch_desired_median*500.0/MAX_ANGLE_RAD
        self.pitch_neutral = numpy.clip(self.pitch_neutral,1440,1560)
        rospy.logwarn('new pitch neutral value = ' + str(self.pitch_neutral) + ' in [1440,1560]')

        return

    def set_k_trottle_neutral(self,throttle_neutral):
        # setting throttle value
        self.throttle_neutral = throttle_neutral
        # for safety better bound this value
        self.throttle_neutral = numpy.clip(self.throttle_neutral,1350,1600)
        rospy.logwarn('settting neutral value to = ' + str(self.throttle_neutral) + ' in [1350,1600]')
        return 

    def reset_parameters(self):
        return 

    def descriptive_message(self):
        # needs to be corrected
        return 'Converter for IRIS+ with parameters' + str(self.throttle_neutral)

    def set_rotation_matrix(self,odometry):

        quaternion = numpy.array([odometry.pose.pose.orientation.x,\
                               odometry.pose.pose.orientation.y,\
                               odometry.pose.pose.orientation.z,\
                               odometry.pose.pose.orientation.w])    

        self.rotation_matrix  = uts.rot_from_quaternion(quaternion)
        # ee = np.array([roll,pitch,yaw]) in DEGREES
        euler_angles     = uts.euler_rad_from_rot(self.rotation_matrix)        

        # euler_angles must come in RADIANS
        self.euler_angles = euler_angles
        return 

    def input_conveter(self,desired_3d_force,yaw_rate_desired):

        self.force_median.update_data(desired_3d_force)

        #---------------------------------------------------------------------#
        # third canonical basis vector
        e3 = numpy.array([0.0,0.0,1.0])
        # rotation_matrix      = uts.rot_from_euler_rad(self.euler_angles)
        rotation_matrix      = self.rotation_matrix
        throttle_unit_vector = numpy.dot(rotation_matrix,e3) 

        # STABILIZE MODE:APM COPTER
        # The throttle sent to the motors is automatically adjusted based on the tilt angle
        # of the vehicle (i.e increased as the vehicle tilts over more) to reduce the 
        # compensation the pilot must fo as the vehicles attitude changes

        # computing desired Throttle, desired roll angle, pitch angle, and desired yaw rate
        # throttle will be smaller when tilted (compensates for adjustsments done onboard)
        Throttle = numpy.dot(desired_3d_force,throttle_unit_vector)
        # TODO: remark here
        # Throttle = numpy.linalg.norm(desired_3d_force)

        # this decreases the throtle, which will be increased (by internal controller)
        # I commented this out, because throtlled was being clipped at minimum (1000)
        # Throttle = Throttle*numpy.dot(throttle_unit_vector,e3)


        roll_desired,pitch_desired = self.roll_pitch(desired_3d_force)

        #---------------------------------------------------------------------#
        # degrees per second
        MAX_PSI_SPEED_Deg = self.MAX_PSI_SPEED_Deg
        MAX_PSI_SPEED_Rad = MAX_PSI_SPEED_Deg*numpy.pi/180.0

        MAX_ANGLE_DEG = self.MAX_ANGLE_DEG
        MAX_ANGLE_RAD = MAX_ANGLE_DEG*numpy.pi/180.0

        #---------------------------------------------------------------------#
        # input for IRIS+ comes in specific order
        # [U[0],U[1],U[2],U[3]] = [roll,pitch,throttle,yaw]
        U = numpy.zeros(4)

        #---------------------------------------------------------------------#
        # angles comand between 1000 and 2000 PWM

        # Roll
        U[0]  =  self.roll_neutral + self.roll_compensation*roll_desired*500.0/MAX_ANGLE_RAD;    
        # Pitch
        U[1]  =  self.pitch_neutral - self.pitch_compensation*pitch_desired*500.0/MAX_ANGLE_RAD;    
        # Yaw
        U[3]  =  yaw_rate_desired*500.0/MAX_PSI_SPEED_Rad;    
        # Throttle
        U[2]  = Throttle*self.throttle_neutral/(self.__GRAVITY*self.total_mass);

        # need to bound between to maximum limits of roll pitch yaw thrust
        U[0:2]= np.clip(U[0:2],-0.25,0.25)
        U[2]  = np.clip(U[2],0,1.5)
        U[3]  = np.clip(U[3],-0.25,0.25)


        return U

    def roll_pitch(self,Full_actuation):

        psi = self.euler_angles[2]

        #--------------------------------------#
        # Rz(psi)*Ry(theta_des)*Rx(phi_des) = n_des
        # desired roll and pitch angles
        norm = numpy.linalg.norm(Full_actuation)
        if norm > 0.1*self.__GRAVITY*self.total_mass:
            n_des     = Full_actuation/norm
            n_des_rot = uts.rot_z(-psi).dot(n_des)
        else:
            n_des     = numpy.array([0.0,0.0,1.0])
            n_des_rot = uts.rot_z(-psi).dot(n_des)


        sin_phi   = -n_des_rot[1]
        sin_phi   = numpy.clip(sin_phi,-1,1)
        phi       = numpy.arcsin(sin_phi)

        sin_theta = n_des_rot[0]/numpy.cos(phi)
        sin_theta = numpy.clip(sin_theta,-1,1)
        cos_theta = n_des_rot[2]/numpy.cos(phi)
        cos_theta = numpy.clip(cos_theta,-1,1)
        pitch     = numpy.arctan2(sin_theta,cos_theta)

        return (phi,pitch)
