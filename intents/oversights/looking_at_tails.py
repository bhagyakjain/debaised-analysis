"""
Copyright 2020 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""This module detects the oversight 'Looking at tails to find causes'
when the top-k oversight is called.

This oversight occurs when the user sorts according a metric and some other
metric which he has requested for remaing same for the entire list as it is
in the top-k entries. Here the user might get misleaded by seeing the other
metric - he might make wrong view that only in the top-k this metric looks
like this. But actually the metric is closeby for the entire list.

Todo(when the date format is updated) - add the test for date columns
"""
import sys
sys.path.append(".")

import math
from util import constants

def looking_at_tails(result_table, k, metric):
    """This function gives suggestions if 'looking at tails to find causes'
    oversight is detected in the results generated by the top-k.

    The cut-off is fixed in the util/constants module

    Args:
        topk_results: Type-pandas dataframe
            contain the results without cropping rows not in top-k.
        k: integer
            It is the number of entries to be taken in the top-k results.
        metric: str
            It is the column name of the metric column

    Todo(after completion of all oversights) : normalize it so that
        it can be compared with other oversight's parameter

    Returns:
        suggestion : dictonary with keys 'suggestions', 'oversight_name',
                     'is_column_level_suggestion', 'col_list'.
    """
    # this oversight won't apply if all rows are included
    if k == -1:
        return

    # list of columns where the oversight occurs
    # initalized to a empty list
    col_list = []

    # iterating over all columns in the table
    for column in result_table.columns:

        if column != metric:

            if str(result_table[column].dtype) in ['float64', 'int64']:
            	# real number column

                parameter = _get_param_in_float_column(result_table[column], k)

                if parameter <= constants.LOOKING_AT_THE_TAILS_FLOAT_THRESHOLD:
                    col_list.append({'column':column, 'confidence_score':parameter})

            elif str(result_table[column].dtype) in ['object'] and \
                 len(set(result_table[column])) in [2, 3]:
            	# binary/ternary variable column

                parameter = _get_param_in_string_column(result_table[column], k)
                print(column, parameter)

                if parameter <= constants.LOOKING_AT_THE_TAILS_STRING_THRESHOLD:
                    col_list.append({'column':column, 'confidence_score':parameter})

    if len(col_list) == 0:
        return
    else:
        suggestion = {}
        suggestion['suggestion'] = 'Values in these columns for the top-k rows are similar for other rows also'
        suggestion['oversight_name'] = 'Looking at tails to find causes'
        suggestion['is_column_level_suggestion'] = True
        suggestion['col_list'] = col_list
        return suggestion

def _get_param_in_float_column(column, k):
    """This function returns the parameter for the real number column.
    Column passed should contain real numbers (int or float).

    Uses parameter =  | Average 1 - Average 2 | / SD 
    group 1 = top-k
    group 2 = others

    Args:
        column: type - pandas.core.series.Series
                contains the values present in the column
    Returns:
        float: value of the parameter
    """
    standard_deviation = column.std()

    average_of_topk = column[:k].mean()

    average_of_others = column[k:].mean()

    deciding_parameter = abs(average_of_others - average_of_topk) / standard_deviation

    return deciding_parameter

def _get_param_in_string_column(column, k):
    """This function returns the parameter in .
    Column passed should contain binary/ternary variables

    The paraeter used is the angele between tf(term frequency) vector of the topk
    and the tf vector of the entire table

    Args:
        column: type - pandas.core.series.Series
                contains the values present in the column
    Returns:
        float: value of the parameter
    """
    topk_entries = column[:k]

    other_entries = column[k:]

    vector_topk = {entry:0 for entry in column}
    for entry in topk_entries:
        vector_topk[entry] += 1

    vector_others = {entry:0 for entry in column}
    for entry in other_entries:
        vector_others[entry] += 1

    return _angle_between_vectors(vector_topk, vector_others)

def _angle_between_vectors(vector_1, vector_2):
    """ Calculates the angle in between the 2 rank vectors.
    Uses dot product to calculate the cosine of the angle, then math.acos to
    convert into angle.

    Args:
        vector_1, vector_2: Type-Dict
            The Angle is calculated in between these 2 vectors.
            The keys of the vector are the axis of the vector,
            and values are the length in that axis.
    Returns:
        The angle in between the 2 vectors in degree.
    """
    cross_product = 0
    magnitude1 = 0
    magnitude2 = 0

    for x in vector_1.keys():
        cross_product = cross_product + vector_1[x] * vector_2[x]
        magnitude1 = magnitude1 + vector_1[x] * vector_1[x]
        magnitude2 = magnitude2 + vector_2[x] * vector_2[x]

    cosine_angle = cross_product / (math.sqrt(magnitude1 * magnitude2))

    angle = math.acos(cosine_angle)

    # angle in degrees
    angle = angle * 180 / math.pi

    return angle
