#!/usr/bin/env python
# this line is just used to define the type of document
"""This is a dynamic controller, not a static controller"""

# in case we want to use rospy.logwarn or logerror
import rospy

import numpy

from utilities import utility_functions

import json

from controllers_hierarchical import controller

# import dictionary with available double integrator controllers
from controllers_hierarchical.double_integrator_controllers import database_dic


class BoundedIntegralPIDController(controller.Controller):

    
    @classmethod
    def contained_objects(cls):
        return {"double_integrator_controller": database_dic.database_dic}


    @classmethod
    def description(cls):
        return "PID Controller, with saturation on integral part"
    
    
    @classmethod
    def parameters_to_string(cls, \
            double_integrator_controller = database_dic.database_dic["DefaultDIC"],\
            integral_gain_xy   = 0.0, \
            bound_integral_xy  = 0.0, \
            integral_gain_z    = 0.5, \
            bound_integral_z   = 0.0,
            quad_mass          = 1.66779
            ):

        params = {
            #TODO should we change the value of this item to also include the class name?
            'double_integrator_controller': (double_integrator_controller.__name__, double_integrator_controller.parameters_to_string()),\
            'integral_gain_xy'   :integral_gain_xy     ,\
            'bound_integral_xy'  :bound_integral_xy    ,\
            'integral_gain_z'    :integral_gain_z      ,\
            'bound_integral_z'   :bound_integral_z     ,
            'quad_mass'          :quad_mass
            }

        return json.dumps(params, indent=4)


    @classmethod
    def string_to_parameters(cls, string):
        
        dic = json.loads(string)
        
        for key, value in cls.contained_objects().items():
            inner_obj = dic[key]
            InnerCls = value[inner_obj[0]]
            #rospy.logwarn(InnerCls)
            inner_params_str = inner_obj[1]
            inner_params = json.loads(inner_params_str)
            if inner_params == None:
                inner_params = dict()
            dic[key] = InnerCls(**inner_params)
            
        return dic

    def __init__(self,\
            double_integrator_controller = database_dic.database_dic["DefaultDIC"] ,\
            integral_gain_xy     = 0.0        ,\
            bound_integral_xy    = 0.0        ,\
            integral_gain_z      = 0.5        ,\
            bound_integral_z     = 0.0        ,\
            quad_mass            = 1.66779
            ):

        self.__integral_gain_xy     = integral_gain_xy
        self.__bound_integral_xy    = bound_integral_xy

        self.__integral_gain_z      = integral_gain_z
        self.__bound_integral_z     = bound_integral_z

        # di_controller_class_name = 'DefaultDIController'
        self.DIControllerObject  = double_integrator_controller

        #TODO should these two be inherited by a parent instead?
        # Should the mass be passed as a parameter?
        # We can always use 1.66779 as a default value
        self.__quad_mass = quad_mass
        
        self.MASS = quad_mass
        self.GRAVITY = 9.81

        self.disturbance_estimate   = numpy.array([0.0,0.0,0.0])
        self.d_est = self.disturbance_estimate

        self.t_old  = 0.0

        pass


    def __str__(self):
        #TODO add the remaining parameters
        string = controller.Controller.__str__(self)
        string += "\nDouble-integrator controller: " + str(self.DIControllerObject)
        return string
        

    def output(self, delta_t, state, reference):

        # third canonical basis vector
        e3 = numpy.array([0.0,0.0,1.0])        
        
        #--------------------------------------#
        # position and velocity
        x  = state[0:3]; v  = state[3:6]

        #--------------------------------------#
        # desired quad trajectory
        xd = reference[0:3];
        vd = reference[3:6];
        ad = reference[6:9];
        
        #--------------------------------------#
        # position error and velocity error
        ep = x - xd
        ev = v - vd

        u,u_p,u_v,u_p_p,u_v_v,u_p_v,Vpv,VpvD,V_p,V_v,V_v_p,V_v_v = self.DIControllerObject.output(ep,ev)

        Full_actuation = self.MASS*(ad + u + self.GRAVITY*e3 - self.d_est)


        # -----------------------------------------------------------------------------#
        # update disturbance estimate

        gains_integral_action    = numpy.array([self.__integral_gain_xy ,self.__integral_gain_xy ,self.__integral_gain_z ])
        max_disturbance_estimate = numpy.array([self.__bound_integral_xy,self.__bound_integral_xy,self.__bound_integral_z])

        # derivatice of disturbance estimate (ELEMENT WISE PRODUCT)
        

        d_est_dot  = gains_integral_action*V_v
        # new disturbance estimate
        t_new = delta_t
        disturbance_estimate = self.disturbance_estimate + d_est_dot*(t_new - self.t_old) 
        # saturate estimate just for safety (element wise bound)
        self.disturbance_estimate = utility_functions.bound(disturbance_estimate,max_disturbance_estimate,-1.0*max_disturbance_estimate)
        # update old time
        self.t_old = t_new

        return Full_actuation


    def reset_disturbance_estimate(self):
        self.disturbance_estimate = numpy.array([0.0,0.0,0.0])
        return


# #Test

# inner_objs = BoundedIntegralPIDController.contained_objects()
# print inner_objs

# Dic = inner_objs['double_integrator_controller']['DoubleIntegratorBoundedNotComponentWiseController']
# print Dic

# dic_parameters = Dic.string_to_parameters(Dic.parameters_to_string())
# print dic_parameters

# dic = Dic(**dic_parameters)
# print dic

# params = BoundedIntegralPIDController.string_to_parameters(BoundedIntegralPIDController.parameters_to_string())
# print params

# params['double_integrator_controller'] = dic
# print params

# con = BoundedIntegralPIDController(**params)
# print con
# print con.output(0.0, numpy.zeros(9), numpy.zeros(9))


