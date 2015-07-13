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

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from os.path import dirname, realpath, join

pychrm_test_dir = dirname( realpath( __file__ ) ) #WNDCHARM_HOME/tests/pywndchrm_tests
wndchrm_test_dir = join( dirname( pychrm_test_dir ), 'wndchrm_tests' )
test_dir = wndchrm_test_dir

from wndcharm.FeatureSpace import FeatureSpace
from wndcharm.FeatureWeights import FisherFeatureWeights

class TestFisherFeatureWeights( unittest.TestCase ):
	"""Fisher score calculation"""

	epsilon = 0.00001

	test_fit_path = join( test_dir,'test-l.fit' )
	test_normalized_fit_path = join( test_dir, 'test_fit-l-normalized.fit' )
	test_feat_weight_path = join( test_dir,'test_fit-l.weights' )
	
	# --------------------------------------------------------------------------
	def test_NewFromFeatureSet( self ):
		"""Fisher score calculation"""

		feature_set = FeatureSpace.NewFromFitFile( self.test_fit_path )
		feature_set.Normalize( inplace=True )
		result_weights = FisherFeatureWeights.NewFromFeatureSpace( feature_set )

		# test weights generated from test-l.fit:
		# wndchrm classify -l -f1.0 -vtest_fit-l.weights test-l.fit test-l.fit 
		target_weights = FisherFeatureWeights.NewFromFile( self.test_feat_weight_path )

	 	for target_val, res_val in zip( target_weights.values, result_weights.values ):
			self.assertAlmostEqual( target_val, res_val, delta=self.epsilon )

if __name__ == '__main__':
	unittest.main()
