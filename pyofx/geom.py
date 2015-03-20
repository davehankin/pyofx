"""
Geom

A module for performing Euler rotations, customized for working with Orcaflex.

Currently includes 2 rotation sequences:

    'xyz' Corresponds to Orcaflex Rotations 1-2-3
    'zyz' Corresponds to Orcaflex Azimuth-Declination-Gamma
    
Usage:
    import geom
    geom.convert_angles()
    
Prompts user to enter Azimuth, Declination and Gamma, then copies Orcaflex Rotations 1-2-3
to clipboard

Dependencies:
    pyperclip

written by davehankin on 20-Mar-2015

"""

import math
import numpy as np
import pyperclip

class Ucs:
    
    def __init__(self, 
                 origin=np.array([0,0,0], dtype=float), 
                 xaxis=np.array([1,0,0], dtype=float), 
                 yaxis=np.array([0,1,0], dtype=float), 
                 zaxis=np.array([0,0,1], dtype=float)
                 ):

        self.origin = np.asarray(origin)
        self.xaxis = np.asarray(xaxis)
        self.yaxis = np.asarray(yaxis)
        self.zaxis = np.asarray(zaxis)

    def __setattr__(self, attr, value):
        if attr == 'origin' or attr == 'xaxis' or \
                attr == 'yaxis' or attr == 'zaxis':
            self.__dict__[attr] = np.asarray(value)
        else:
            raise AttributeError(attr + 'not allowed')
        
    def __str__(self):
        
        str1 = ','.join('{:>10.4f}'.format(x) for x in self.origin)
        str2 = ','.join('{:>10.4f}'.format(x) for x in self.xaxis)
        str3 = ','.join('{:>10.4f}'.format(x) for x in self.yaxis)
        str4 = ','.join('{:>10.4f}'.format(x) for x in self.zaxis)

        return ' origin: %s\n' % str1 + \
               '      x: %s\n' % str2 + \
               '      y: %s\n' % str3 + \
               '      z: %s\n' % str4

    def rotate_euler(self, centre, angles, sequence):
        
        v = self.origin - centre
        R = rotate(angles, sequence)
        self.origin = R.dot(v) + centre
        self.xaxis = R.dot(self.xaxis)
        self.yaxis = R.dot(self.yaxis)
        self.zaxis = R.dot(self.zaxis)

    def rotate_axis_angle(self, centre, axis, angle):
        
        v = self.origin - centre
        R = axis_angle(axis, angle)
        self.origin = R.dot(v) + centre
        self.xaxis = R.dot(self.xaxis)
        self.yaxis = R.dot(self.yaxis)
        self.zaxis = R.dot(self.zaxis)

    def get_euler_angles(self, sequence):
        
        R = np.zeros((3,3))
        R[:,0] = self.xaxis
        R[:,1] = self.yaxis
        R[:,2] = self.zaxis
        
        return euler_angles(R, sequence)


def rotate(angles, sequence):
    """
    Returns rotation matrix associated with intrinsic euler rotations:
        'xyz' corresponds to Orcaflex Rotation 1-2-3
        'zyz' corresponds to Orcaflex azi-dec-gamma
    """
    
    r1 = math.radians(angles[0])
    r2 = math.radians(angles[1])
    r3 = math.radians(angles[2])
    
    c1 = math.cos(r1)
    c2 = math.cos(r2)
    c3 = math.cos(r3)
    
    s1 = math.sin(r1)
    s2 = math.sin(r2)
    s3 = math.sin(r3)
    
    R = np.zeros((3,3))
    
    # xyz is same as Orcaflex Rotation 1-2-3
    if sequence == 'xyz':
        R[0,0] = c2*c3
        R[0,1] = -c2*s3
        R[0,2] = s2
        R[1,0] = c1*s3 + c3*s1*s2
        R[1,1] = c1*c3 - s1*s2*s3
        R[1,2] = -c2*s1
        R[2,0] = s1*s3 - c1*c3*s2
        R[2,1] = c3*s1 + c1*s2*s3
        R[2,2] = c1*c2
    
    # zyz is same as Orcaflex azi-dec-gamma
    elif sequence == 'zyz':
        R[0,0] = c1*c2*c3 - s1*s3
        R[0,1] = -c3*s1 - c1*c2*s3
        R[0,2] = c1*s2
        R[1,0] = c1*s3 + c2*c3*s1
        R[1,1] = c1*c3 - c2*s1*s3
        R[1,2] = s1*s2
        R[2,0] = -c3*s2
        R[2,1] = s2*s3
        R[2,2] = c2

    return R


def axis_angle(axis, theta):
    """
    Returns the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    theta = np.asarray(theta)
    axis = axis/math.sqrt(np.dot(axis, axis))
    a = math.cos(theta/2)
    b, c, d = -axis*math.sin(theta/2)
    aa, bb, cc, dd = a*a, b*b, c*c, d*d
    bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
    
    R = np.array([[aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
                  [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
                  [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]])
                       
    return R


def euler_angles(rot, sequence):
    """
    Returns the intrinsic euler angles for a given rotation matrix based on sequence:
        'xyz' corresponds to Orcaflex Rotation 1-2-3
        'zyz' corresponds to Orcaflex azi-dec-gamma
    """
    if sequence == 'xyz':
        r1 = -math.atan2(rot[1,2], rot[2,2])
        r2 = math.asin(rot[0,2])
        r3 = -math.atan2(rot[0,1], rot[0,0])
        
    if sequence == 'zyz':
        r1 = math.atan2(rot[1,2], rot[0,2])
        r2 = math.acos(rot[2,2])
        r3 = math.atan2(rot[2,1], -rot[2,0])
        
    return [math.degrees(r1),
            math.degrees(r2),
            math.degrees(r3)]


def convert_angles():
    """
    Converts Orcaflex azi-dec-gamma to Rotation 1-2-3
    """
    
    azi = float(raw_input('Enter azimuth (0 to 360): '))
    dec = float(raw_input('Enter declination (0 to 180): '))
    gamma = float(raw_input('Enter gamma (0 to 360): '))
    
    ucs = Ucs()
    ucs.rotate_euler([0,0,0], [azi,dec,gamma], 'zyz')
    r123 = ucs.get_euler_angles('xyz')

    s = '\t'.join(['{0:.4f}'.format(x) for x in r123])
    pyperclip.copy(s)
    