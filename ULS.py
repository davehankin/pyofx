class ULSResult(object):

    def __init__(self, ):
        """ ULSResult - extreme value statistics. 
        arguments:
        time_history - The TimeHistory to process with Extreme statistics.
        extreme - "Max" or "Min" for extrema to analyse.

        Methods:
                Result.extreme_stats() - runs extreme stats on a Result object which has a valid time_history attribute

        Output:
                Result.time_history = values from ULS.extract.
                Result.threshold_factor = factor applied to maximum value to obtain exceedence threshold.
                Result.exeecdence_threshold = value fo exceedence threshold used.
                Result.maximum_most_probable_level = Most probable value.

        """
        self.time_history = time_history
        self.sample_interval = sample_interval


    

    def __str__(self):

        header = """\n<--- %s %s for %s --->\n""" % (
            self.variable, self.extreme, self.ofxobject)
        region = filter(lambda a: a[0] != None,
                        zip([self.node, self.section, self.arc_length],
                            ['Node', 'Section', 'Arc Length(m)']))
        if region:
            text_region = """[%s = %s]""" % (region[0][1], str(region[0][0]))
        else:
            text_region = ""
        final_values = """
        with a %1.1f threshold factor applied to yield %f exceedance threshold,
the most probable 3hr return value is:\n\n%f\n""" % (self.threshold_factor,
                                                     self.exeecdence_threshold,
                                                     self.maximum_most_probable_level)
        return header + text_region + final_values


def process_uls_folder(direcetory, data_to_extract):
    """ 
    data_to_extract should be a list of ULSResult objects 
    e.g. data_to_extract = [ULSResult('Line1','Curvature', 'Max')] 

    """
    models = Models(direcetory, filetype='sim')
    g = models[0]['General']
    log_interval = g.ActualLogSampleInterval

    def time_histories(obj, result):

        def end_or_mid(node, range):
            if node == 0:
                obj_extra = oeEndA
            elif node == len(range):
                obj_extra = oeEndB
            else:
                obj_extra = oeNodeNum(node)
            return obj_extra

        if result.node:
            time_history = obj.TimeHistory(
                result.variable, Period(1), oeNodeNum(result.node))
        elif result.arc_length:
            time_history = obj.TimeHistory(result.variable, Period(1),
                                           oeArcLength(result.arc_length))
        elif result.section:
            if result.extreme == 'Max':
                range = obj.RangeGraph(result.variable, Period(1),
                                       arclengthRange=arSpecifiedSections(result.section,
                                                                          result.section))
                max_range = range.Max
                arc_range = range.X
                max_var = max_range.max()
                max_var_node = max_range.argmax()
                time_history = obj.TimeHistory(result.variable, Period(1),
                                               oeArcLength(arc_range[max_var_node]))

            elif result.extreme == 'Min':
                range = obj.RangeGraph(result.variable, Period(1),
                                       arclengthRange=arSpecifiedSections(result.section,
                                                                          result.section))
                min_range = range.Min
                arc_range = range.X
                min_var = min_range.min()
                min_var_node = min_range.argmin()
                time_history = obj.TimeHistory(result.variable, Period(1),
                                               oeArcLength(arc_range[min_var_node]))
            else:
                raise IOError("Needs to be 'Max' or 'Min'.")
        else:

            if result.extreme == 'Max':
                max_range = obj.RangeGraph(result.variable, Period(1)).Min
                max_var = max_range.max()
                max_var_node = max_range.argmax()
                obj_extra = end_or_mid(max_var_node, max_range)
                time_history = obj.TimeHistory(
                    result.variable, Period(1), obj_extra)
            elif result.extreme == 'Min':
                min_range = obj.RangeGraph(result.variable, Period(1)).Min
                min_var = min_range.min()
                min_var_node = min_range.argmin()
                obj_extra = end_or_mid(min_var_node, min_range)
                time_history = obj.TimeHistory(
                    result.variable, Period(1), obj_extra)
        return time_history

    for m in models:
        if m.simulationComplete:
            for result in data_to_extract:

                obj = m[result.ofxobject]
                result.time_history += list(time_histories(obj, result))
                result.log_interval = log_interval
        else:
            print "NOT COMPLETE:\n{}\n{}".format(m.path, m.status)

    results = [result.extreme_stats() for result in data_to_extract]
    return results
