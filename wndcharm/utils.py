"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                                               
 Copyright (C) 2015 National Institutes of Health 

    This library is free software; you can redistribute it and/or              
    modify it under the terms of the GNU Lesser General Public                 
    License as published by the Free Software Foundation; either               
    version 2.1 of the License, or (at your option) any later version.         
                                                                               
    This library is distributed in the hope that it will be useful,            
    but WITHOUT ANY WARRANTY; without even the implied warranty of             
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU          
    Lesser General Public License for more details.                            
                                                                               
    You should have received a copy of the GNU Lesser General Public           
    License along with this library; if not, write to the Free Software        
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA  
                                                                               
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                                               
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 Written by:  Christopher Coletta (github.com/colettace)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


# wndcharm.py has the definitions of all the SWIG-wrapped primitive C++ WND_CHARM objects.
import wndcharm
import numpy as np

# ============================================================
# BEGIN: Initialize module level globals
Algorithms = []
Transforms = []

def initialize_module(): 
    """If you're going to calculate any features, you need this stuff.
    FIXME: Rig this stuff to load only on demand."""
    
    global Algorithms
    global Transforms
    # The verbosity is set by the environment variable WNDCHRM_VERBOSITY, in wndchrm_error.cpp
    # wndcharm.cvar.verbosity = 7

    # These are the auto-registered ComputationTasks, which come in different flavors
    all_tasks = wndcharm.ComputationTaskInstances.getInstances()
    for task in all_tasks:
        if task.type == task.ImageTransformTask:
            Transforms.append (task)
#            print task.name + " added to Transforms"
        elif task.type == task.FeatureAlgorithmTask:
            Algorithms.append (task)
#            print task.name + " added to Algorithms"

    # The standard feature plans get loaded as needed from C++ statics, so they don't need to be initialized.
    # Standard sets (other plan "parts" are in Tasks.h under StdFeatureComputationPlans)
    #     getFeatureSet();
    #     getFeatureSetColor();
    #     getFeatureSetLong();
    #     getFeatureSetLongColor();

    # e. g.:
#     small_feature_plan = wndcharm.StdFeatureComputationPlans.getFeatureSet()
#     print "small feature set groups:"
#     last_feature_group = None;
#     for i in range( 0, small_feature_plan.n_features):
#         feature_group = small_feature_plan.getFeatureGroupByIndex(i)
#         feature_name = small_feature_plan.getFeatureNameByIndex(i)
#         if feature_group.name != last_feature_group:
#             print "feature_group "+feature_group.name
#         last_feature_group = feature_group.name
#         print "  feature_name "+feature_name

    # while we're debugging, raise exceptions for numerical weirdness, since it all has to be dealt with somehow
    # In cases where numerical weirdness is expected and dealt with explicitly, these exceptions are
    # temporarily turned off and then restored to their previous settings.
    np.seterr (all='raise')

# ============================================================
def output_railroad_switch( method_that_prints_output ):
    """This is a decorator that optionally lets the user specify a file to which to redirect
    STDOUT. To use, you must use the keyword argument "output_filepath" and optionally
    the keyword argument "mode" """

    def print_method_wrapper( *args, **kwargs ):
        
        retval = None
        if "output_filepath" in kwargs:
            output_filepath = kwargs[ "output_filepath" ]
            del kwargs[ "output_filepath" ]
            if "mode" in kwargs:
                mode = kwargs[ "mode" ]
                del kwargs[ "mode" ]
            else:
                mode = 'w'
            print 'Saving output of function "{0}()" to file "{1}", mode "{2}"'.format(\
                  method_that_prints_output.__name__, output_filepath, mode )
            import sys
            backup = sys.stdout
            sys.stdout = open( output_filepath, mode )
            retval = method_that_prints_output( *args, **kwargs )
            sys.stdout.close()
            sys.stdout = backup
        elif "output_stream" in kwargs:
            output_stream = kwargs[ "output_stream" ]
            del kwargs[ "output_stream" ]
            print 'Saving output of function "{0}()" to stream'.format(\
                  method_that_prints_output.__name__)
            import sys
            backup = sys.stdout
            try:
                sys.stdout = output_stream
                retval = method_that_prints_output( *args, **kwargs )
            finally:
                sys.stdout = backup
        else:
            retval = method_that_prints_output( *args, **kwargs )
        return retval

    return print_method_wrapper

# ============================================================
def normalize_by_columns( full_stack, mins=None, maxs=None ):
    """This is a global function to normalize a matrix by columns.
    If numpy 1D arrays of mins and maxs are provided, the matrix will be normalized against these ranges
    Otherwise, the mins and maxs will be determined from the matrix, and the matrix will be normalized
    against itself. The mins and maxs will be returned as a tuple.
    Out of range matrix values will be clipped to min and max (including +/- INF)
    zero-range columns will be set to 0.
    NANs in the columns will be set to 0.
    The normalized output range is hard-coded to 0-100
    """
# Edge cases to deal with:
#   Range determination:
#     1. features that are nan, inf, -inf
#        max and min determination must ignore invalid numbers
#        nan -> 0, inf -> max, -inf -> min
#   Normalization:
#     2. feature values outside of range
#        values clipped to range (-inf to min -> min, max to inf -> max) - leaves nan as nan
#     3. feature ranges that are 0 result in nan feature values
#     4. all nan feature values set to 0

# Turn off numpy warnings, since we're taking care of invalid values explicitly
    oldsettings = np.seterr(all='ignore')
    if (mins is None or maxs is None):
        # mask out NANs and +/-INFs to compute min/max
        full_stack_m = np.ma.masked_invalid (full_stack, copy=False)
        maxs = full_stack_m.max (axis=0)
        mins = full_stack_m.min (axis=0)

    # clip the values to the min-max range (NANs are left, but +/- INFs are taken care of)
    full_stack.clip (mins, maxs, full_stack)
    # remake a mask to account for NANs and divide-by-zero from max == min
    full_stack_m = np.ma.masked_invalid (full_stack, copy=False)

    # Normalize
    full_stack_m -= mins
    full_stack_m /= (maxs - mins)
    # Left over NANs and divide-by-zero from max == min become 0
    # Note the deep copy to change the numpy parameter in-place.
    full_stack[:] = full_stack_m.filled (0) * 100.0

    # return settings to original
    np.seterr(**oldsettings)

    return (mins,maxs)

# END: Initialize module level globals
#===============================================================


# BEGIN: Class definitions for WND-CHARM intermediate objects

#############################################################################
# class definition of SampleImageTiles
#############################################################################

class SampleImageTiles (object):
    """SampleImageTiles is an image iterator wrapper (the iterator is the sample method).
    The iterator is wrapped to provide additional information such as the number of samples that will
    be extracted from the image, as well as information about each sample after calling the sample method.
    Each call to sample returns the next wndcharm.ImageMatrix in the sample set.
    The constructor has three required parameters.
    The image parameter can be a path to an image file or a wndcharm.ImageMatrix
    The x and y parameters can specify the number of non-overlapping samples in each dimension (is_fixed parameter is False),
    or the dimentions of each sample (is_fixed parameter is True).
    Example usage:
        image_iter = SampleImageTiles (input_image, size_x, size_y, True)
        print "Number of samples = "+str (image_iter.samples)
        for sample in image_iter.sample():
            print "({0},{1}) : ({2},{3})".format (
                image_iter.current_x, image_iter.current_y, sample.width, sample.height)
    """

    downsample = 0
    mean = 0
    stddev = 0
    def __init__( self, image_in, x, y, is_fixed=False ):

        from os.path import exists
        if isinstance( image_in, str ):
            if not exists( image_in ):
                raise ValueError( "The file '{0}' doesn't exist, maybe you need to specify the full path?".format( image_in ) )
            self.image = wndcharm.ImageMatrix()
            if 1 != self.image.OpenImage( image_in, 0, None, 0, 0 ):
                raise ValueError( 'Could not build an ImageMatrix from {0}, check the file.'.format( image_in ) )
        elif isinstance( image_in, wndcharm.ImageMatrix ):
            self.image = image_in
        else:
            raise ValueError("image parameter 'image_in' is not a string or a wndcharm.ImageMatrix")

        if (is_fixed):
            self.tile_width = x
            self.tile_height = y
            self.tiles_x = int (self.image.width / x)
            self.tiles_y = int (self.image.height / y)
        else:
            self.tile_width = int (self.image.width / x)
            self.tile_height = int (self.image.height / y)
            self.tiles_x = x
            self.tiles_y = y

        self.samples = self.tiles_x * self.tiles_y
        self.current_row = 0
        self.current_y = 0
        self.current_col = 0
        self.current_x = 0

    def sample(self):
        width = self.tile_width
        height = self.tile_height
        max_x = self.image.width
        max_y = self.image.height
        original = self.image
        while self.current_y + height <= max_y:
            while self.current_x + width <= max_x:
                new_px_plane = wndcharm.ImageMatrix()
                bb = ( self.current_x, self.current_y,
                        self.current_x + width - 1, self.current_y + height - 1 )
                new_px_plane.submatrix( original, *bb ) # no retval
                yield new_px_plane
                self.current_x += width
                self.current_col += 1
            self.current_y += height
            self.current_row += 1

initialize_module()

def compare( a_list, b_list, atol=1e-7 ):
    """Helps to compare floating point values to values stored
    in text files (ala .fit and .sig files) where the number of
    significant figures is sometimes orders of magnitude different"""

    result = True
    errcount = 0
    for count, (a_raw, b_raw) in enumerate( zip( a_list, b_list ) ):
        if errcount > 20:
            break

        if a_raw == b_raw:
            continue
        if abs( float( a_raw ) - float( b_raw ) ) < atol:
            continue

        a_str = "{0:0.6g}".format( a_raw )
        b_str = "{0:0.6g}".format( b_raw )

        # These deal with the 1e-6 ~ 6.93e-7 comparison issue
        # a_addl_zero = ""
        # b_addl_zero = ""

        exp_digits = 0
        e_in_a_str = 'e' in a_str
        e_in_b_str = 'e' in b_str
        if e_in_a_str != e_in_b_str:
            errmsg = "Index {0}: \"{1}\" and \"{2}\" exponents don't match."
            print errmsg
            result = False
            errcount += 1
            continue
            #self.fail( errmsg.format( count, a_str, b_str, ) )
        if e_in_a_str:
            a_coeff, a_exp = a_str.split( 'e' )
            b_coeff, b_exp = b_str.split( 'e' )
            if a_exp != b_exp:
                # AssertionError: Index 623: "1e-06" and "6.93497e-07" exponents don't match.
                a_exp = int( a_exp )
                b_exp = int( b_exp )
#                    if a_exp > b_exp:
#                        a_addl_zero = '0'* abs( a_exp - b_exp )
#                    else:
#                        b_addl_zero = '0'* abs( a_exp - b_exp )
                exp_digits = abs( a_exp - b_exp )

                #errmsg = "Index {0}: \"{1}\" and \"{2}\" exponents don't match."
                #self.fail( errmsg.format( count, a_raw, b_raw, ) )
            # FIXME: lstrip doesn't properly deal with negative numbers
            a_int_str = a_coeff.translate( None, '.' ).lstrip('0')
            b_int_str = b_coeff.translate( None, '.' ).lstrip('0')
        else:
            a_int_str = a_str.translate( None, '.' ).lstrip('0')
            b_int_str = b_str.translate( None, '.' ).lstrip('0')

        a_len = len( a_int_str )
        b_len = len( b_int_str )
        diff_digits = abs( a_len - b_len ) + exp_digits
        tail = '0' * diff_digits

        #msg = 'a_str "{0}" (len={1}), b_str "{2}" (len={3}), tail="{4}"'
        #print msg.format( a_int_str, a_len, b_int_str, b_len, tail )

        if a_len > b_len:
#                a = int( a_int_str + a_addl_zero )
#                b = int( b_int_str + tail + b_addl_zero )
#            else:
#                a = int( a_int_str + tail + a_addl_zero )
#                b = int( b_int_str + b_addl_zero )
            a = int( a_int_str )
            b = int( b_int_str + tail )
        elif b_len > a_len:
            a = int( a_int_str + tail )
            b = int( b_int_str )
        else:
            a = int( a_int_str )
            b = int( b_int_str )
        # Rounding is useless, since due to floating point's inexact representation
        # it's possible to have 2.65 round to 2.6
        #a = round( a, -1 * diff_digits )
        #b = round( b, -1 * diff_digits )

        diff = abs( a - b )

        #print "{0}->{1}=={2}<-{3} : {4} <= {5}".format( a_raw, a, b, b_raw, diff, 10 ** diff_digits )
        if diff > 10 ** diff_digits:      
            errstr = "Index {0}: {1} isn't enough like {2}".format( count, a_raw, b_raw )
            print errstr
            result = False
            errcount += 1
            continue
            #self.fail( errstr.format( count, a_raw, b_raw ) )
    return result
