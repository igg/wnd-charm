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


import numpy as np
from .utils import output_railroad_switch
from .FeatureSpacePredictionExperiment import FeatureSpaceClassificationExperiment

#============================================================================
class _BaseGraph( object ):
    """An abstract base class that is supposed to hold onto objects on which to call
    matplotlib.pyplot API methods."""

    def __init__( self ):

        # general stuff:
        self.chart_title = None
        self.file_name = None
        self.split_result = None

        # pyplot-specific stuff
        self.figure = None
        self.main_axes = None

    def SaveToFile( self, filepath ):
    
        if self.figure == None:
            raise ValueError( 'No figure to save!' )
        self.figure.savefig( filepath )
        print 'Wrote chart "{0}" to file "{1}"'.format( self.chart_title, filepath )
            
#============================================================================
class PredictedValuesGraph( _BaseGraph ):
    """This is a concrete class that can produce two types of graphs that are produced
    from SingleSamplePrediction data stored in a FeatureSpacePrediction."""

    #=================================================================
    def __init__( self, result, name=None, use_averaged_results=True ):
        """Constructor sorts ground truth values contained in FeatureSpacePrediction
        and loads them into self.grouped_coords
        
        use_averaged_results - bool - If this object has averaged results (due to tiling or 
            "per sample" aggregation across splits, use those results instead of 
            individual results."""

        #FIXME: implement user-definable bin edges

        self.split_result = result
        if name is None:
            name = result.name

        self.chart_title = name

        gt_vals, pred_vals = result.RankOrderSort( use_averaged_results=use_averaged_results )
        whole_list = zip( gt_vals, pred_vals )

        self.grouped_coords = {}

        if result.test_set.discrete:
            self.class_names = result.test_set.class_names
            self.class_values = result.test_set.interpolation_coefficients
            self.num_classes = result.test_set.num_classes
            for class_val, class_name in zip( self.class_values, self.class_names ):
                self.grouped_coords[ class_name ] = \
                        [ xy for xy in whole_list if xy[0] == class_val ]
        else:
            class_name = result.test_set.name
            self.class_names = [ class_name ]
            self.class_values = [ 1 ]
            self.num_classes = 1
            self.grouped_coords[ class_name ] = whole_list

        _min = min( self.class_values )
        ampl = max( self.class_values ) - _min
     
        import matplotlib.pyplot as plt
        self.class_colors = plt.cm.jet( [ float(val -_min)/ampl for val in self.class_values ] )

    #=====================================================================
    @classmethod
    @output_railroad_switch
    def NewFromHTMLReport( cls, filepath, use_averaged_results=True ):
        """Helper function to facilitate the fast generation of graphs from C++-generated
        HTML Report files."""

        exp = FeatureSpaceClassificationExperiment.NewFromHTMLReport( filepath )
        exp.GenerateStats()
        exp.PerSampleStatistics( quiet=True )
        newgraphobj = cls( exp, use_averaged_results=use_averaged_results )
        return newgraphobj

    #=====================================================================
    def RankOrderedPredictedValuesGraph( self, chart_title=None ):
        """This graph visualizes the distribution of predicted values generated by classification.
        For each individual ImageClassification with ground truth value (i.e., class id) and
        predicted value, all results are grouped within their class, sorted by predicted value
        in ascending order, then ploted side-by-side.
        
        Required the package matplotlib to be installed."""

        print "Rendering rank-ordered predicted values graph"
        import matplotlib
        # Need following line to generate images on servers, see
        # http://matplotlib.org/faq/howto_faq.html#generate-images-without-having-a-window-appear
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        self.figure = plt.figure( figsize=(20,20) )
        self.main_axes = self.figure.add_subplot(111)

        if chart_title:
            self.chart_title = chart_title
        self.main_axes.set_title( self.chart_title )
        self.main_axes.set_xlabel( 'count' )
        self.main_axes.set_ylabel( 'Predicted Value Scores' )

        abscissa_index = 1

        for class_name, class_color in zip( self.class_names, self.class_colors ):
            ground_truth_vals, predicted_vals = zip( *self.grouped_coords[ class_name ] )
            x_vals = [ i + abscissa_index for i in range( len( ground_truth_vals ) ) ]
            self.main_axes.scatter( x_vals, predicted_vals, c=class_color, marker='o',
                    s=150, edgecolor='none', label=class_name )
            abscissa_index += len( ground_truth_vals )

        #self.main_axes.legend( loc = 'lower right')
        self.main_axes.legend( loc = 'lower right')
        return self.figure
        
    #=====================================================================
    def KernelSmoothedDensityGraph( self, chart_title=None ):
        """This graph visualizes the distribution of predicted values generated by classification.
        A kernel-smoothed probability density function is plotted for each image class on
        the same chart allowing comparison of distribution of predicted values amoung image class.
        
        Requires the packages matplotlib and scipy. Uses scipy.stats.gaussian_kde to
        generate kernel-smoothed probability density functions."""

        print "Rendering kernel-smoothed probability density estimate graph"
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        self.figure = plt.figure( figsize=(20,20) )
        self.main_axes = self.figure.add_subplot(111)
        if chart_title:
            self.chart_title = chart_title

        self.main_axes.set_title( self.chart_title )
        self.main_axes.set_xlabel( 'Age score' )
        self.main_axes.set_ylabel( 'Probability density' )

        from scipy.stats import gaussian_kde

        for class_name, class_color in zip( self.class_names, self.class_colors ):
            ground_truth_vals, predicted_vals = zip( *self.grouped_coords[ class_name ] )

            pred_vals = np.array( predicted_vals )
            lobound = pred_vals.min()
            hibound = pred_vals.max()
            kernel_smoother = gaussian_kde( pred_vals )
            intervals = np.mgrid[ lobound:hibound:100j ]
            density_estimates = kernel_smoother.evaluate( intervals )
            self.main_axes.plot( intervals, density_estimates, c=class_color,
                linewidth=6, label=class_name )

        self.main_axes.legend()
        return self.figure

#============================================================================
class FeatureTimingVersusAccuracyGraph( _BaseGraph ):
    """A cost/benefit analysis of the number of features used and the time it takes to calculate
    that number of features for a single image"""

    #FIXME: Add ability to do the first 50 or 100 features, make the graph, then
    #       ability to resume from where it left off to do the next 50.

    def __init__( self, training_set, feature_weights, test_image_path,
        chart_title=None, max_num_features=300 ):

        self.timing_axes = None
        import time
        timings = []

        from wndcharm.FeatureSpacePredictionExperiment import FeatureSpaceClassificationExperiment
        from wndcharm.SingleSamplePrediction import SingleSampleClassification
        from wndcharm.FeatureSpacePrediction import FeatureSpaceClassification

        experiment = FeatureSpaceClassificationExperiment( training_set, training_set, feature_weights )
        for number_of_features_to_use in range( 1, max_num_features + 1 ):

            reduced_ts = None
            reduced_fw = None
            three_timings = []
            # Take the best of 3
            for timing in range( 3 ):
                # Time the creation and classification of a single signature
                t1 = time.time()
                reduced_fw = feature_weights.Threshold( number_of_features_to_use )
                sig = FeatureVector( source_filepath=test_image_path, feature_names=reduced_fw.feature_names ).GenerateFeatures()
                reduced_ts = training_set.FeatureReduce( reduced_fw )
                sig.Normalize( reduced_ts )
        
                result = SingleSampleClassification.NewWND5( reduced_ts, reduced_fw, sig )
                result.Print()
                # FIXME: save intermediates just in case of interruption or parallization
                # result.PickleMe()
                t2 = time.time()
                three_timings.append( t2 - t1 )

            timings.append( min( three_timings ) )

            # now, do a fit-on-fit test to measure classification accuracy
            split_result = FeatureSpaceClassification.NewWND5( reduced_ts, reduced_ts, reduced_fw )
            split_result.Print()
            experiment.individual_results.append( split_result )

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        x_vals = list( range( 1, max_num_features + 1 ) )

        self.figure = plt.figure()
        self.main_axes = self.figure.add_subplot(111)
        if chart_title == None:
            self.chart_title = "Feature timing v. classification accuracy"    
        else:
            self.chart_title = chart_title
        self.main_axes.set_title( self.chart_title )
        self.main_axes.set_xlabel( 'Number of features' )
        self.main_axes.set_ylabel( 'Classification accuracy (%)', color='b' )
        classification_accuracies = \
          [ split_result.classification_accuracy * 100 for split_result in experiment.individual_results ]

        self.main_axes.plot( x_vals, classification_accuracies, color='b', linewidth=2 )
        for tl in self.main_axes.get_yticklabels():
            tl.set_color('b')    

        self.timing_axes = self.main_axes.twinx()
        self.timing_axes.set_ylabel( 'Time to calculate features (s)', color='r' )
        self.timing_axes.plot( x_vals, timings, color='r' )
        for tl in self.timing_axes.get_yticklabels():
            tl.set_color('r')    

#============================================================================
class AccuracyVersusNumFeaturesGraph( _BaseGraph ):
    """Graphing the figure of merit a a function of number of features"""

    # FIXME: roll this class into FeatureTimingVersusAccuracyGraph, allowing
    # both Discrete and continuous data

    def __init__( self, training_set, feature_weights, chart_title=None, min_num_features=1, max_num_features=None, step=5, y_min=None, y_max=None, quiet=False):

        from wndcharm.FeatureSpacePredictionExperiment import FeatureSpaceRegressionExperiment
        from wndcharm.SingleSamplePrediction import SingleSampleRegression
        from wndcharm.FeatureSpacePrediction import FeatureSpaceRegression

        ls_experiment = FeatureSpaceRegressionExperiment( training_set, training_set, feature_weights, name="Least Squares Regression Method")
        voting_experiment = FeatureSpaceRegressionExperiment( training_set, training_set, feature_weights, name="Voting Method")
        if max_num_features is None:
            max_num_features = len( feature_weights )

        x_vals = range( min_num_features, max_num_features + 1, step )

        for number_of_features_to_use in x_vals:
            reduced_fw = feature_weights.Threshold( number_of_features_to_use )
            reduced_ts = training_set.FeatureReduce( reduced_fw )
            if not quiet:
                reduced_fw.Print()

            ls_split_result = FeatureSpaceRegression.NewLeastSquares( reduced_ts, None, reduced_fw, split_number=number_of_features_to_use, quiet=my_quiet )
            if not quiet:
                ls_split_result.Print()
            ls_experiment.individual_results.append( ls_split_result )

            voting_split_result = FeatureSpaceRegression.NewMultivariateLinear( reduced_ts, reduced_fw, split_number=number_of_features_to_use )
            if not quiet:
                voting_split_result.Print()
            voting_experiment.individual_results.append( voting_split_result )

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        self.figure = plt.figure( figsize=(12, 8) )
        self.main_axes = self.figure.add_subplot(111)
        if chart_title == None:
            self.chart_title = "R vs. num features, two methods"
        else:
            self.chart_title = chart_title

        # need to make axes have same range
        ls_yvals = [ split_result.std_err for split_result in ls_experiment.individual_results ]
        voting_yvals = [ split_result.std_err for split_result in voting_experiment.individual_results ]

        min_ls_yval = min(ls_yvals)
        optimal_num_feats_ls = ls_yvals.index( min_ls_yval ) + 1 # count from 1, not 0
        min_voting_yval = min(voting_yvals)
        optimal_num_feats_voting = voting_yvals.index( min_voting_yval ) + 1 # count from 1, not 0

        all_vals = ls_yvals + voting_yvals

        if y_min is not None:
            try:
                y_min = float(y_min)
            except:
                raise ValueError( "Can't convert {0} to float".format(y_min))
            _min = y_min
        else:
            _min = min( all_vals )
        if y_max is not None:
            try:
                y_max = float(y_max)
            except:
                raise ValueError( "Can't convert {0} to float".format(y_max))
            _max = y_max
        else:
            _max = max( all_vals )

        # Plot least Squares Data
        self.main_axes.set_title( self.chart_title )
        self.main_axes.set_xlabel( 'Number of features' )
        self.main_axes.set_ylabel( 'RMS Least Squares Method', color='b' )
        self.main_axes.set_ylim( [_min, _max ] )
        self.main_axes.plot( x_vals, ls_yvals, color='b', marker='o', linestyle='--' )
        for tl in self.main_axes.get_yticklabels():
            tl.set_color('b')

        self.main_axes.annotate( 'min R={0:.3f} @ {1}'.format(min_ls_yval, optimal_num_feats_ls),
        color='b',
        xy=( optimal_num_feats_ls, min_ls_yval ),
        xytext=( optimal_num_feats_ls, 0.8 * _max ),
        arrowprops=dict(facecolor='black', shrink=0.05),
        horizontalalignment='right' )

        # Plot Voting method data
        self.timing_axes = self.main_axes.twinx()
        self.timing_axes.set_ylabel( 'RMS Voting Method', color='r' )
        self.timing_axes.set_ylim( [_min, _max ] )
        self.timing_axes.plot( x_vals, voting_yvals, color='r', marker='o', linestyle='--' )
        for tl in self.timing_axes.get_yticklabels():
            tl.set_color('r')

        self.timing_axes.annotate( 'min R={0:.3f} @ {1}'.format(min_voting_yval, optimal_num_feats_voting),
        color='r',
        xy=( optimal_num_feats_voting, min_voting_yval ),
        xytext=( optimal_num_feats_voting, 0.6 * _max ),
        arrowprops=dict(facecolor='black', shrink=0.05),
        horizontalalignment='right' )

#============================================================================
#class Dendrogram( object ):
#    """Not implemented. In the future might use scipy.cluster (no unrooted dendrograms though!)
#    or Biopython.Phylo to visualize. Perhaps could continue C++ implementation's use of PHYLIP's
#    Fitch-Margoliash program "fitch" to generate Newick phylogeny, and visualize using
#    native python tools."""
#    pass
