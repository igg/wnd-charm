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
from .FeatureSpace import FeatureSpace, CheckIfClassNamesAreInterpolatable
from .FeatureSpacePrediction import _FeatureSpacePrediction, FeatureSpaceClassification,\
        FeatureSpaceRegression
from .FeatureWeights import FisherFeatureWeights, PearsonFeatureWeights
from .SingleSamplePrediction import SingleSampleClassification, SingleSampleRegression, \
        AveragedSingleSamplePrediction

#============================================================================
class _FeatureSpacePredictionExperiment( _FeatureSpacePrediction ):
    """Base class container for FeatureSpacePrediction instances,
    i.e., when classifying/regressing a FeatureSpace multiple times, as in train/test splits.
    Methods here aggregate results and calculate statistics across splits.

    Instance Attributes:
    --------------------
        self.averaged_results - list of instances of AveragedSingleSamplePredictions,
            used to collect statistics on sample predictions across splits
    """

    def __init__( self, *args, **kwargs ):
        """Possible kwargs, with defaults:
        training_set=None, test_set=None, feature_weights=None, name=None, split_number=None"""

        super( _FeatureSpacePredictionExperiment, self ).__init__( *args, **kwargs )
        # declared on base class
        #self.averaged_results = None
        self.feature_weight_statistics = None

    #=====================================================================
    def __len__( self ):
        try:
            return len( self.individual_results )
        except:
            return 0

    #=====================================================================
    def GenerateStats( self ):
        """Aggregation of ground truth->predicted value pairs for all samples across splits.
        Aggregate feature weight statistics.

        Use the function PerSampleStatistics() to average results for specific
             images across splits.

        Considerations for analyzing prediction results:
        1. The test set may or may not have ground truth (discrete and continuous)
        2. The results may not have a predicted value (discrete only)
        3. Continuous classifications do not have marginal probabilities
        4. Hybrid test sets (discrete test sets loaded into a continuous test set)
           have "pseudo-classes," i.e., easily binnable ground truth values."""

        from itertools import chain
        lists_of_ground_truths = []
        lists_of_predicted_values = []

        for split_result in self.individual_results:
            # Call GenerateStats() on the individual batches if the
            # ground truth->predicted value pairs haven't been scraped
            # from the batch's list of individual _SingleSamplePrediction objects.
            if split_result.std_err == None and split_result.classification_accuracy == None:
                split_result.GenerateStats()

            if split_result.averaged_results:
                classification_results = split_result.averaged_results
                ground_truth_values = split_result.averaged_ground_truth_values
                predicted_values = split_result.averaged_predicted_values
            else:
                classification_results = split_result.individual_results
                ground_truth_values = split_result.ground_truth_values
                predicted_values = split_result.predicted_values

            self.num_classifications += len( classification_results )
            if ground_truth_values:
                lists_of_ground_truths.append( ground_truth_values )
            if predicted_values:
                lists_of_predicted_values.append( predicted_values )

        if lists_of_ground_truths:
            self.ground_truth_values = list( chain( *lists_of_ground_truths ) )
        if lists_of_predicted_values:
            self.predicted_values = list( chain( *lists_of_predicted_values ) )

        # Aggregate feature weight statistics across splits, if any:
        feature_weight_lists = {}
        for split_result in self.individual_results:
            if not split_result.feature_weights:
                continue
            weight_names_and_values = zip( split_result.feature_weights.feature_names,
                                                        split_result.feature_weights.values)
            for name, weight in weight_names_and_values:
                if not name in feature_weight_lists:
                    feature_weight_lists[ name ] = []
                feature_weight_lists[ name ].append( weight )

        if feature_weight_lists is not {}:
            for feature_name in feature_weight_lists:
                feature_weight_lists[ feature_name ] = \
                        np.array( feature_weight_lists[ feature_name ] )

            feature_weight_stats = []
            for fname in feature_weight_lists:
                fwl = feature_weight_lists[ fname ]
                count = len( fwl )
                fwl_w_zeros = np.zeros( len( self.individual_results ) )
                fwl_w_zeros[0:count] = fwl
                feature_weight_stats.append( ( np.mean( fwl_w_zeros ),
                                count, np.std(fwl), np.min(fwl), np.max(fwl), fname ) )

            # Sort on mean values, i.e. index 0 of tuple created above
            self.feature_weight_statistics = sorted( feature_weight_stats, key=lambda a: a[0], reverse=True )
        return self

    #=====================================================================
    @classmethod
    @output_railroad_switch
    def FeatureWeightsGridSearch( cls, start=None, stop=None, step=10, **kwargs ):
        """Takes same args as NewShuffleSplit. Calls ShuffleSplit for varying number of features.
        
        Returns the instance of FeatureSpacePredictionExperiment that has best figure of merit."""

        best_exp = None
        max_classification_accuracy = 0
        features_accuracy_dict = {}

        try:
            for n_features in xrange( start, stop, step ):
                exp = cls.NewShuffleSplit( **kwargs ).GenerateStats()
                features_accuracy_dict[ n_features ] = exp.classification_accuracy
                if exp.classification_accuracy > max_classification_accuracy:
                    best_exp = exp
                    max_classification_accuracy = exp.classification_accuracy
        finally:
            print "==================================================="
            for n_features in sorted( features_accuracy_dict.keys() ):
                print n_features, ',' , features_accuracy_dict[ n_features ] 
            print "==================================================="
            best_exp.features_accuracy_dict = features_accuracy_dict

        return best_exp

#        print ""
#        print "Aggregate feature weight analysis:"
#        print "-----------------------------------"
#        print "Legend:"
#        print "NUM - Number of features used in aggregate / Individual feature rank"
#        print "ASE - Standard Error of Final Predicted Value (using aggregated feature) vs ground truth"
#        print "APC - Pearson correlation coefficient of Final Predicted Values vs ground truth"
#        print "APE - Standard Error of APC"
#        print "APP - P-value of APC"
#        print "ASC - Spearman correlation coefficient of Final Predicted Values vs ground truth"
#        print "APP - P-value of ASC"
#        print ""
#
#        print "NUM\tASE\tAPC\tAPE\tAPP\tASC\tAPP"
#        print "===\t===\t===\t===\t===\t===\t==="
#        for result in self.individual_results:
#            line_item = "{0}\t".format( len( result.feature_weights.values ) ) # NUM
#            line_item += "{0:.4f}\t".format( result.std_err ) # ASE
#            line_item += "{0:.4f}\t".format( result.pearson_coeff ) # APC
#            line_item += "{0:.4f}\t".format( result.pearson_std_err ) # APE
#            line_item += "{0:.4f}\t".format( result.pearson_p_value ) # APP
#            line_item += "{0:.4f}\t".format( result.spearman_coeff ) # ASC
#            line_item += "{0:.4f}\t".format( result.spearman_p_value ) # ASP
#            print line_item

    #=====================================================================
    @classmethod
    def NewShuffleSplit( cls, feature_space, n_iter=5, name=None, features_size=0.15,
                           train_size=None, test_size=None, random_state=True, classifier=None,
                           quiet=False, display=15 ):
        """args train_size, test_size, and random_state are all passed through to Split()
        feature_size if a float is feature usage fraction, if in is top n features."""

        # Splitting will result in a call to _RebuildViews and SortSamplesByGroundTruth
        # so we have to make sure that the input FeatureSpace is sorted too
        feature_space = feature_space.SortSamplesByGroundTruth( \
                rebuild_views=True, inplace=False, quiet=True )

        if not name:
            name = feature_space.name

        experiment = cls( training_set=feature_space, test_set=feature_space, name=name )
        if isinstance( features_size, float ):
            if features_size < 0 or features_size > 1.0:
                raise ValueError('Arg "features_size" must be on interval [0,1] if a float.')
            num_features = int( round( features_size * feature_space.num_features ) )
        elif isinstance( features_size, int ):
            if features_size < 0 or features_size > feature_space.num_features:
                raise ValueError( 'must specify num_features or feature_usage_fraction in kwargs')
            num_features = features_size
        else:
            raise ValueError( 'Arg "features_size" must be valid float or int.' )

        if not quiet:
            print "using top " + str( num_features ) + " features"

        # If you passed the same random_state into Split, you'd get the same exact split for
        # all n_iter. Therefore use the seed passed in here to predictably generate seeds
        # for the Split() iterations.
        if random_state:
            from numpy.random import RandomState
            from functools import partial
            maxint = 2 ** 32 - 1
            if random_state is True:
                from numpy.random import randint as np_randint
                randint = partial( np_randint, low=0, high=maxint )
            elif type( random_state ) is int:
                randint = partial( RandomState( random_state ).randint, low=0, high=maxint )
            elif type( random_state ) is RandomState:
                randint = partial( random_state.randint, low=0, high=maxint )
            else:
                raise ValueError( "arg random_state must be an int, instance of numpy.random.RandomState, or True")
            experiment.use_error_bars = True
        else:
            # Samples split the same way all iterations,
            # not useful except for testing results aggregation:
            randint = lambda: None
            experiment.use_error_bars = False

        for split_index in range( n_iter ):
            if not quiet:
                print "=========================================="
                print "SHUFFLE SPLIT ITERATION", str( split_index )
            train_set, test_set = feature_space.Split(
                train_size, test_size, random_state=randint(), quiet=quiet )
            train_set.Normalize( quiet=quiet )
            
            if feature_space.discrete:
                weights = \
                  FisherFeatureWeights.NewFromFeatureSpace( train_set ).Threshold( num_features )
            else:    
                weights = \
                  PearsonFeatureWeights.NewFromFeatureSpace( train_set ).Threshold( num_features )

            if not quiet:
                weights.Print( display=display )
            reduced_train_set = train_set.FeatureReduce( weights, quiet=quiet )
            reduced_test_set = test_set.FeatureReduce( weights, quiet=quiet )
            reduced_test_set.Normalize( reduced_train_set, quiet=quiet )

            if feature_space.discrete:
                split_result = FeatureSpaceClassification.NewWND5( reduced_train_set, \
                 reduced_test_set, weights, split_number=split_index, quiet=quiet,\
                 error_bars=experiment.use_error_bars )
            else:
                if classifier == 'linear':
                    split_result = FeatureSpaceRegression.NewMultivariateLinear(
                            reduced_train_set, weights, split_number=split_index, quiet=quiet )
                else: # default classifier == 'lstsq':
                    split_result = FeatureSpaceRegression.NewLeastSquares(
                        reduced_train_set, reduced_test_set, weights, split_number=split_index, quiet=quiet )

            split_result.GenerateStats()
            if not quiet:
                split_result.Print()

            experiment.individual_results.append( split_result )

        if not quiet:
            experiment.Print()
        return experiment

    #=====================================================================
    @output_railroad_switch
    def PerSampleStatistics( self, print_indiv=True, quiet=False ):
        """Characterizes variability of regressed predicted values across batches.
        _SingleSamplePrediction info is aggregated for each individual sample,
        statistics calculated and printed out.
        
        returns self for convenience.
        quiet - bool - if True, just do the average"""

        if self.individual_results == 0:
            raise ValueError( 'No batch results to analyze' )

        from collections import defaultdict
        accumulated_results = defaultdict( list )
        self.averaged_results = []

        # Coallate:
        for split in self.individual_results:
            for result in split.individual_results:
                accumulated_results[ result.source_filepath ].append( result )

        self.averaged_results = [ AveragedSingleSamplePrediction( reslist,
                self.training_set.class_names ) \
                    for reslist in accumulated_results.values() ]

        # sort by ground truth above, then sample name
        self.averaged_results.sort( key=lambda res: res.ground_truth_label )
        self.averaged_results.sort( key=lambda res: res.ground_truth_value )
        self.averaged_results.sort( key=lambda res: res.source_filepath )

        self.averaged_predicted_values, self.averaged_ground_truth_values = zip(
            *[ (res.predicted_value, res.ground_truth_value ) for res in self.averaged_results ] )

        if quiet:
            return self

        first_time_through = True
        for avg_res in self.averaged_results:
            avg_res.Print( line_item=True, include_name=True, include_col_header=first_time_through,\
                    training_set_class_names=self.training_set.class_names )
            if print_indiv and len( avg_res.individual_results ) > 1:
                for res in avg_res.individual_results:
                    res.Print( line_item=True, include_name=True,
                        include_split_number=True )
            first_time_through = False

        return self

#============================================================================
class FeatureSpaceClassificationExperiment( _FeatureSpacePredictionExperiment ):
    """Container for FeatureSpaceClassifications instances,
    i.e., when classifying a FeatureSpace multiple times, as in train/test splits.
    Methods here aggregate results and calculate statistics across splits.

    The information contained here comprises everything that would appear in an
    HTML file generated by the C++ implementation of WND-CHARM."""

    obj_count = 0

    def __init__( self, *args, **kwargs ):
        """Possible kwargs, with defaults:
        training_set=None, test_set=None, feature_weights=None, name=None, split_number=None"""

        super( FeatureSpaceClassificationExperiment, self ).__init__( *args, **kwargs )

        self.num_correct_classifications = None
        self.classification_accuracy = None
        self.std_err = None

        self.num_classifications_per_class = None
        self.num_correct_classifications_per_class = None

        self.confusion_matrix = None
        self.average_similarity_matrix = None
        self.average_class_probability_matrix = None

    #==============================================================    
    def __str__( self ):
        outstr = '<' + self.__class__.__name__
        if self.split_number is not None:
            outstr += ' #' + str( self.split_number )
        if self.name:
            outstr += ' "' + self.name + '"'
        if self.individual_results:
            outstr += ' n_splits=' + str( len( self.individual_results ) )
        if self.num_classifications:
            outstr += ' n_calls=' + str( self.num_classifications )
        if self.num_correct_classifications:
            outstr += ' n_corr=' + str( self.num_correct_classifications )
        if self.classification_accuracy is not None:
            outstr += ' acc={0:0.2f}%'.format( self.classification_accuracy * 100 )
        if self.std_err is not None:
            outstr += ' std_err={0:0.2f}%'.format( self.std_err )
        return outstr + '>'
    #==============================================================
    def __repr__( self ):
        return str(self)
    #=====================================================================
    def GenerateStats( self ):
        """Generate confusion, similarity, average class probability matrices
        from constituent iterations."""

        # Base class does feature weight analysis, aggregation of ground truth &
        # predicted values
        super( FeatureSpaceClassificationExperiment, self ).GenerateStats()
        
        # Initialize the matrices:

        # Remember! Dicts are not guaranteed to maintain key order but lists are
        # When cycling through the matrix, iterate over the lists
        # and not the keys of the dict.
        from collections import defaultdict # introduced Python 2.5

        # These are dicts of dicts in the form:
        # self.confusion_matrix[ <Ground Truth Class> ][ <Predicted Class> ] == count
        self.confusion_matrix = defaultdict( lambda: defaultdict( int ) )
        self.average_class_probability_matrix = defaultdict( lambda: defaultdict( float ) )

        self.num_correct_classifications = 0

        self.num_classifications_per_class = defaultdict( int )
        self.num_correct_classifications_per_class = defaultdict( int )

        self.num_classifications = 0
        # Iterate over all the splits:
        for split_result in self.individual_results:
            if split_result.classification_accuracy == None:
                split_result.GenerateStats()
            self.num_classifications += len( split_result )
            # Iterate over the rows in the confusion matrix:
            for gt_class in self.test_set.class_names:
                gt_row_dict = split_result.confusion_matrix[ gt_class ]
                # Iterate over the columns in the confusion matrix:
                for pred_class in self.training_set.class_names:
                    if pred_class not in gt_row_dict:
                        # Important to try to add 0 since it will create that cell 
                        # in the matrix in the defaultdict if it doesn't exist yet.
                        count = 0
                    else:
                        count = gt_row_dict[ pred_class ]
                    self.confusion_matrix[ gt_class ][ pred_class ] += count
                    self.num_classifications_per_class[ gt_class ] += count
                    if gt_class == pred_class:
                        self.num_correct_classifications += count
                        self.num_correct_classifications_per_class[ gt_class ] += count

                    self.average_class_probability_matrix[ gt_class ][ pred_class ] += \
                      split_result.average_class_probability_matrix[ gt_class ][ pred_class ]

        # Finalize the Average Class Probability Matrix by dividing each marginal
        # probability sum by the number of splits:
        # FIXME: This assumes there were an equal number of classifications in each batch
        for row in sorted( self.test_set.class_names ):
            for col in sorted( self.training_set.class_names ):
                self.average_class_probability_matrix[ row ][ col ] /= len( self )

        # The similarity matrix is just the average class probability matrix
        # normalized to have 1's in the diagonal.
        # Doesn't make sense to do this unless the matrix is square
        # if row labels == column labels:
        if self.test_set.class_names == self.training_set.class_names:
            from copy import deepcopy
            self.similarity_matrix = deepcopy( self.average_class_probability_matrix )
            for row in self.test_set.class_names:
                denom = self.similarity_matrix[ row ][ row ]
                for col in self.training_set.class_names:
                    self.similarity_matrix[ row ][ col ] /= denom

        self.classification_accuracy = float( self.num_correct_classifications) / float( self.num_classifications )
        return self

    #=====================================================================
    @output_railroad_switch
    def Print( self, display=20 ):
        """Generate and output statistics across all batches, as well as the figures of merit
        for each individual batch."""
        
        if self.classification_accuracy == None:
            self.GenerateStats()

        if self.feature_weight_statistics:
            n_feature_weights = len( self.feature_weight_statistics )
            if n_feature_weights <= display:
                if n_feature_weights > 0:
                    display = n_feature_weights
                    print "Displaying feature weight statistics for all {0} features".format(
                            display )
        else:
            display = False

        print '='*50
        s = self.__class__.__name__
        if self.name:
            s += ' "' + self.name + '"'
        s += " (" + str( len( self.individual_results ) ) + " iterations)"
        print s

        acc = self.classification_accuracy
        n = self.num_classifications
        n_correct = self.num_correct_classifications

        if not self.use_error_bars:
            print "{0}/{1} correct = {2:0.2f}%".format( n_correct, n, acc * 100 )
        else:
            # Using either normal approximation of binomial distribution or the Wilson score interval
            # to calculate standard error of the mean, depending on the situation.
            # For more info, see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
            # The confidence interval is S.E.M. * quantile for your chosen accuracy
            # The quantile for 95% accuracy is ~ 1.96.
            z = 1.95996
            z2 = 3.84144 # z^2

            from math import sqrt

            # This is a rule of thumb test to check whecther sample size is large enough
            # to use normal approximation of binomial distribution:
            if ((n * acc) > 5) and ((n * (1 - acc)) > 5):
                # Using normal approximation:
                std_error_of_mean = sqrt( acc * (1-acc) / n )
                conf_interval = z * std_error_of_mean
                print "{0}/{1} correct = {2:0.2f} +/- {3:0.2f}% w/ 95% conf. (normal approx. interval)".format(
                    n_correct, n, acc * 100, conf_interval * 100 )
            else:
                # Using Wilson approximation:
                # This term goes to 1 as number of classifications gets large:
                coeff = 1 / (1+(z2/n))
                raw_acc = acc
                # Wilson accuracy modifies the raw accuracy for low n:
                acc = coeff * (raw_acc + z2/(2*n))
                conf_interval = coeff * z * sqrt( (raw_acc*(1-raw_acc)/n) + (z2/(4*n**2)) )

                outstr = "{0}/{1} correct = {2:0.1f}% raw accuracy".format(
                    n_correct, n, raw_acc * 100, conf_interval * 100 )
                outstr += " ({0:0.2f} +/- {1:0.2f}% w/ 95% conf. (Wilson score interval))".format(
                        acc * 100, conf_interval * 100)
                print outstr

        print self.ConfusionMatrix(), '\n'
        print self.SimilarityMatrix(), '\n'
        print self.AvgClassProbMatrix(), '\n'

        if display:
            outstr = "{0}\t{1:0.3f}\t{2:>3}\t{3:0.3f}\t{4:0.3f}\t{5:0.3f}\t{6}"
            print "Feature Weight Analysis (top {0} features):".format( display )
            print "Rank\tmean\tcount\tStdDev\tMin\tMax\tName"
            print "----\t----\t-----\t------\t---\t---\t----"
            for count, fw_stat in enumerate( self.feature_weight_statistics[:display], 1 ):
                print outstr.format( count, *fw_stat )

    #=====================================================================
    @classmethod
    @output_railroad_switch
    def NewFromHTMLReport( cls, path_to_html ):
        """Takes as input an HTML report generated by C++ implementation wndchrm
        Parses the report and builds up a Pychrm representation of the results,
        which facilitates analysis, graphing, etc."""

        import re
        row_re = re.compile( r'<tr>(.+?)</tr>' )
        name_re = re.compile( r'"(.+?)"' )
        num_re = re.compile( r'(\d*\.?\d+)' )

        # FIXME: This should fail if there isn't some part of the class names that are interpretable
        # as a number, specifically when it tries to calculate an "interpolated" (predicted) value
        # for the sample based on marginal probabilities.

        def ParseClassSummaryHTML( the_html ):
            rows = row_re.findall( the_html )
            ts = FeatureSpace()
            ts.num_classes = 0
            ts.interpolation_coefficients = []
            ts.class_names = []
            for rownum, row in enumerate( rows ):
                if rownum == 0:
                    continue # skip column header
                ts.num_classes += 1
                classname = re.search( r'<th>(.+?)</th>', row ).group(1)
                ts.class_names.append( classname )
            ts.interpolation_coefficients = CheckIfClassNamesAreInterpolatable( ts.class_names )
            return ts

        # The following will be determined once the number of classes has been ascertained
        normalization_col = 1
        mp_col = 2
        ground_truth_col = None
        predicted_col = None
        interp_val_col = None # We don't even use this
        name_col = None

        _training_set = None
        _test_set = None
        exp = cls()
        exp.name = path_to_html

        trainingset_definition = False
        trainingset_html = ""
        testset_definition = False
        testset_html = ""

        insidesplit = False
        split = None
        splitcount = 0
        split_linecount = None
        with open( path_to_html ) as file:
            for line in file:
                if 'trainset_summary' in line:
                    trainingset_definition = True
                elif trainingset_definition == True:
                    trainingset_html += line.strip()
                    if '</table>' in line:
                        trainingset_definition = False
                        ts = _training_set = ParseClassSummaryHTML( trainingset_html )
                        ground_truth_col = ts.num_classes + 3
                        predicted_col = ts.num_classes + 4
                        interp_val_col = ts.num_classes + 6
                        name_col = ts.num_classes + 7

                elif 'testset_summary' in line:
                    testset_definition = True
                elif testset_definition == True:
                    testset_html += line.strip()
                    if '</table>' in line:
                        testset_definition = False
                        _test_set = ParseClassSummaryHTML( testset_html )

                elif line.startswith( '<TABLE ID="IndividualImages_split' ):
                    # If we haven't seen a test set definition by now, we ain't gonna see one period.
                    if not _test_set:
                        _test_set = _training_set
                    insidesplit = True
                    split = FeatureSpaceClassification( training_set=_training_set, test_set=_test_set )
                    split.predicted_values = []
                    split.ground_truth_values = []
                    splitcount += 1
                    split_linecount = 0
                elif insidesplit and line.startswith( '</table><br><br>' ):
                    insidesplit = False
                    exp.individual_results.append( split )
                elif insidesplit:
                    split_linecount += 1
                    if split_linecount == 1:
                        # First line in individual results is column headers
                        # Pure clasification without interpolation
                        if 'Interpolated Value' not in line:
                            interp_val_col = None
                            name_col = ts.num_classes + 6 # one less than set above -- that column won't exist
                        continue
                    noends = line.strip( '<trd/>\n' ) # take the tr and td tags off front end
                    values = noends.split( '</td><td>' )
                    result = SingleSampleClassification()

                    result.normalization_factor = float( values[ normalization_col ] )
                    result.marginal_probabilities = \
                            [ float( val.strip( '</b>' ) ) for val in values[ mp_col : mp_col + _training_set.num_classes ] ]
                    result.predicted_label = values[ predicted_col ]
                    # Sometimes c-chrm labels classes with a * to say it's not part of the training set
                    result.ground_truth_label = values[ ground_truth_col ].strip('*')
                    result.name = name_re.search( values[ name_col ] ).groups()[0]
                    result.source_filepath = result.name
                    if ts.interpolation_coefficients is not None:
                        result.ground_truth_value = \
                        ts.interpolation_coefficients[ ts.class_names.index(result.ground_truth_label ) ]
                        #result.predicted_value = float( values[ interp_val_col ] )
                        result.predicted_value = \
                        sum( [ x*y for x,y in zip( result.marginal_probabilities, _training_set.interpolation_coefficients ) ] )
                        split.predicted_values.append( result.predicted_value )
                        split.ground_truth_values.append( result.ground_truth_value )
                    #result.Print( line_item = True )
                    result.split_number = splitcount
                    split.individual_results.append(result)

        exp.training_set = _training_set
        exp.test_set = _test_set

        exp.GenerateStats()
        return exp

        # If 2 or 3 class problem, plot individuals in marginal probability space
# END class definition for FeatureSpaceClassificationExperiment

#============================================================================
class FeatureSpaceRegressionExperiment( _FeatureSpacePredictionExperiment ):
    """Container for FeatureSpaceRegression instances,
    i.e., when regressing a FeatureSpace multiple times, as in train/test splits.
    Methods here aggregate results and calculate statistics across splits."""

    obj_count = 0

    def __init__( self, *args, **kwargs):
        super( FeatureSpaceRegressionExperiment, self ).__init__( *args, **kwargs )
    #==============================================================    
    def __str__( self ):
        outstr = '<' + self.__class__.__name__
        if self.split_number is not None:
            outstr += ' #' + str( self.split_number )
        if self.name:
            outstr += ' "' + self.name + '"'
        if self.individual_results:
            outstr += ' n=' + str( len( self.individual_results ) )
        if self.std_err is not None:
            outstr += ' R={0:0.2f}'.format( self.std_err )
        return outstr + '>'
    #==============================================================
    def __repr__( self ):
        return str(self)
    #=====================================================================
    def GenerateStats( self ):
        """Calculates statistics describing how well predicted values
        correlate with ground truth across all batches.

        Requires scipy.stats package to be installed"""

        # Base class does feature weight analysis, ground truth-pred. value aggregation
        super( FeatureSpaceRegressionExperiment, self ).GenerateStats()
    
        gt = np.array( self.ground_truth_values )
        pv = np.array( self.predicted_values )
        
        diffs = gt - pv
        diffs = np.square( diffs )
        err_sum = np.sum( diffs )

        from math import sqrt
        from scipy.stats import linregress, spearmanr

        self.std_err = sqrt( err_sum / self.num_classifications )

        # For now, ignore "FloatingPointError: 'underflow encountered in stdtr'"
        np.seterr (under='ignore')
        slope, intercept, self.pearson_coeff, self.pearson_p_value, self.pearson_std_err = \
                                 linregress( self.ground_truth_values, self.predicted_values )

        try:
            self.spearman_coeff, self.spearman_p_value =\
                     spearmanr( self.ground_truth_values, self.predicted_values )
        except FloatingPointError:
            self.spearman_coeff, self.spearman_p_value = ( 0, 1 )

        np.seterr (all='raise')
        return self

    #=====================================================================
    @output_railroad_switch
    def Print( self ):
        """Output statistics from this experiment."""
        if self.std_err == None:
            self.GenerateStats()

        print "\n==========================================="
        print '{0} "{1}"'.format( self.__class__.__name__, self.name )
        print 'Num iterations ("splits"): {0}'.format( len( self.individual_results ) )
        print "Total num classifications: {0}".format( self.num_classifications )
        print "Standard error: {0}".format( self.std_err )
        print "Pearson corellation coefficient: {0}".format( self.pearson_coeff )
        print "Pearson p-value: {0}".format( self.pearson_p_value )        

        outstr = "{0}\t{1:0.3f}\t{2:>3}\t{3:0.3f}\t{4:0.3f}\t{5:0.3f}\t{6}"
        print "Feature Weight Analysis (top 50 features):"
        print "Rank\tmean\tcount\tStdDev\tMin\tMax\tName"
        print "----\t----\t-----\t------\t---\t---\t----"
        for count, fw_stat in enumerate( self.feature_weight_statistics, 1 ):
            print outstr.format( count, *fw_stat )
            if count >= 50:
                break
