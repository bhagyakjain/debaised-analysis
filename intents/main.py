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
"""
This module contains the function that gets called by the UI, and it
serves a purpose of a master function to all the intets.
It returns the result of the intent and also the list of suggestions.
"""


import json, pandas, enum, topk, slice_compare, correlation, trend, time_compare
from flask import escape
from show import show
from util import enums, insert_as_column
from oversights import wrong_points

# ToDo : Change the name hello_http (default name on GCP) to a better name
# that makes sense of the function & also make changes in the UI javascript

def hello_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    
    request_args = request.args

    # extracting the intent parameters from the json
    intent = _get_value(request_json, 'intent')
    table = _get_value(request_json, 'table')
    metric = _get_value(request_json, 'metric')
    dimensions = _get_value(request_json, 'dimensions')
    summary_operator = _get_value(request_json, 'summaryOperator')
    slices = _get_value(request_json, 'slices')
    is_asc = _get_value(request_json, 'isAsc')
    k = _get_value(request_json, 'topKLimit')
    slices = _get_value(request_json, 'slices')
    slice_comparision_arg = _get_value(request_json, 'comparisonValue')
    time_comparision_arg = _get_value(request_json, 'compareDateRange')
    date = _get_value(request_json, 'dateRange')
    time_granularity = _get_value(request_json, 'timeGranularity')
    correlation_metrics = _get_value(request_json, 'correlationMetrics')
    rangeA1Notation = _get_value(request_json, 'rangeA1Notation')



    # Converting the list of list into a pandas dataframe.
    query_table = []
    for row in range(1, len(table)):
        if row != 0:
            query_table.append(table[row])
    query_table_dataframe = pandas.DataFrame(query_table,
                                             columns=table[0])

    (all_dimensions, all_metrics) = _list_all_dimensions_metrics(query_table_dataframe,
                                                                 dimensions, metric)

    # Remove empty columns
    query_table_dataframe = remove_empty_columns(query_table_dataframe)

    # Remove duplicate named columns
    query_table_dataframe = remove_duplicate_named_columns(query_table_dataframe)

    # Converting the variables that contain denote the
    # date range into the desired format.
    date_column_name = None
    date_range = None
    day_first = None
    if date != None:
        date_columns = request_json['dateColumns']
        date_column_name = date['dateCol']
        date_range = (date['dateStart'], date['dateEnd'])
        day_first = date_columns[date_column_name]['day_first']

    # Converting the Slices passed in the json into a
    # list of tuples (col, operator, val)
    slices_list = None
    if slices != None:
        slices_list = []
        for item in slices:
            val = item['sliceVal']
            col = item['sliceCol']
            operator = _str_to_filter_enum(item['sliceOp'])
            slices_list.append((col, operator, val))

    if dimensions == 'null':
        dimensions = None

    if slice_comparision_arg is not None:
        slice_compare_column = slice_comparision_arg['comparisonColumn']
        slice1 = slice_comparision_arg['slice1']
        slice2 = slice_comparision_arg['slice2']

    if time_comparision_arg is not None:
        time_compare_column = time_comparision_arg['dateCol']
        date_range1 = (time_comparision_arg['dateStart1'],
                       time_comparision_arg['dateEnd1'])
        date_range2 = (time_comparision_arg['dateStart2'],
                       time_comparision_arg['dateEnd2'])
        day_first = request_json['dateColumns'][time_compare_column]['day_first']

    if metric == 'null':
        metric = None
    
    summary_operator = _str_to_summary_operator_enum(summary_operator)

    time_granularity = _str_to_time_granularity_enum(time_granularity)

    suggestions = []

    wrong_points_suggestion = wrong_points.wrong_points(query_table_dataframe)

    if intent == 'show':
        query_table_dataframe = show(query_table_dataframe,
                                     slices=slices_list,
                                     metric=metric,
                                     dimensions=dimensions,
                                     summary_operator=summary_operator,
                                     date_column_name=date_column_name,
                                     day_first=day_first,
                                     date_range=date_range
                                    )

        if summary_operator == enums.SummaryOperators.MEAN :
            suggestions.append(get_hardcoded_mean_vs_median_suggestion())
        
        updated_suggestions = []
        for suggestion in suggestions:
            updated_suggestion = suggestion
            if 'change_list' in suggestion.keys():
                updated_suggestion['json'] = func(request_json, suggestion['change_list'])
            updated_suggestions.append(updated_suggestion)

        suggestions = updated_suggestions

                                    
    elif intent == 'topk':
        query_result = topk.topk(query_table_dataframe,
                                 metric, dimensions, is_asc, k,
                                 summary_operator=summary_operator,
                                 slices=slices_list,
                                 date_column_name=date_column_name,
                                 day_first=day_first,
                                 date_range=date_range
                                )
        query_table_dataframe = query_result[0]
        suggestions = query_result[1]
        updated_suggestions = []
        for suggestion in suggestions:
            updated_suggestion = suggestion
            if 'change_list' in suggestion.keys():
                updated_suggestion['json'] = func(request_json, suggestion['change_list'])
            updated_suggestion['oversight'] = updated_suggestion['oversight'].name
            updated_suggestions.append(updated_suggestion)

        suggestions = updated_suggestions


    elif intent == 'slice_compare':
        query_result = slice_compare.slice_compare(query_table_dataframe,
                                                   metric, all_dimensions,
                                                   all_metrics, 
                                                   slice_compare_column,
                                                   slice1, slice2,
                                                   summary_operator,
                                                   date_column_name=date_column_name,
                                                   date_range=date_range,
                                                   day_first = day_first,
                                                   slices=slices_list,
                                                   dimensions = dimensions
                                                   )
        query_table_dataframe = query_result[0]
        suggestions = query_result[1]
        updated_suggestions = []

        for suggestion in suggestions:
            updated_suggestion = suggestion
            if 'change_list' in suggestion.keys():
                updated_suggestion['json'] = func(request_json, suggestion['change_list'])
            updated_suggestion['oversight'] = updated_suggestion['oversight'].name
            updated_suggestions.append(updated_suggestion)

        suggestions = updated_suggestions

    elif intent == 'time_compare':
        query_result = time_compare.time_compare(query_table_dataframe,
                                                 metric, all_dimensions,
                                                 time_compare_column,
                                                 date_range1, date_range2,
                                                 day_first, summary_operator,
                                                 slices=slices_list,
                                                 dimensions = dimensions
                                                 )
        query_table_dataframe = query_result[0]
        suggestions = query_result[1]
        updated_suggestions = []

        for suggestion in suggestions:
            updated_suggestion = suggestion
            if 'change_list' in suggestion.keys():
                updated_suggestion['json'] = func(request_json, suggestion['change_list'])
            updated_suggestion['oversight'] = updated_suggestion['oversight'].name
            updated_suggestions.append(updated_suggestion)

        suggestions = updated_suggestions

    elif intent == 'correlation':
        query_table_dataframe = correlation.correlation(query_table_dataframe,
                                                        correlation_metrics['metric1'],
                                                        correlation_metrics['metric2'],
                                                        slices=slices_list,
                                                        date_column_name=date_column_name,
                                                        day_first=day_first,
                                                        date_range=date_range,
                                                        dimensions=dimensions
                                                        )

    elif intent == 'trend':
        query_table_dataframe = trend.trend(query_table_dataframe,
                                            metric,
                                            time_granularity,
                                            summary_operator,
                                            date_column_name=date_column_name,
                                            day_first=day_first,
                                            date_range=date_range,
                                            slices=slices_list
                                            )

    else:
        raise Exception("Intent name does not match")



    if wrong_points_suggestion is not None:
        wrong_points_suggestion['oversight'] =wrong_points_suggestion['oversight'].name
        suggestions = [wrong_points_suggestion] + suggestions

    final_table = []

    # converting into a json object and returning
    final_table = query_table_dataframe.values.tolist()
    final_table.insert(0, list(query_table_dataframe.columns.values))


    json_ret = {'outputTable' : final_table, 'suggestions' : suggestions}

    if rangeA1Notation is not None :
        all_row_labels = _get_all_row_labels(rangeA1Notation)
        all_column_labels = _get_all_column_labels(rangeA1Notation)
        cheader_to_clabel = _get_cheader_to_clabel(table, all_column_labels)

        if slices_list is not None:
            json_ret['slicing_passed_list'] = insert_as_column.insert_as_column_show(table, cheader_to_clabel, all_row_labels[0], all_row_labels[-1], all_column_labels[0], all_column_labels[-1], slices=slices_list)

        if intent == 'topk' and summary_operator is None:
            filter_column_label_number = _get_number_of_column_label(all_column_labels[-1]) + 1
            filter_column_label = _get_label_from_number(filter_column_label_number)

            json_ret['list_topk_indices'] = insert_as_column.insert_as_column_topk_column(table, cheader_to_clabel, all_row_labels[0], all_row_labels[-1], all_column_labels[0], all_column_labels[-1], filter_column_label, metric, is_asc, k)

    json_string = json.dumps(json_ret)
    return json_string


def _str_to_filter_enum(comparator):
    """
    This function return the corresponding enum to the
    comparator passed.

    Args:
        comparator : Type-str
    Returns:
        Filter enum member
    """
    if comparator == 'Equal to':
        return enums.Filters.EQUAL_TO
    elif comparator == 'Not equal to':
        return enums.Filters.NOT_EQUAL_TO
    elif comparator == 'Less than':
        return enums.Filters.LESS_THAN
    elif comparator == 'Less than equal to':
        return enums.Filters.LESS_THAN_EQUAL_TO
    elif comparator == 'Greater than':
        return enums.Filters.GREATER_THAN
    elif comparator == 'Greater than equal to':
        return enums.Filters.GREATER_THAN_EQUAL_TO
    elif comparator == 'In':
        return enums.Filters.IN
    elif comparator == 'Not In':
        return enums.Filters.NOT_IN
    else:
        return None

def _str_to_summary_operator_enum(summary_operator):
    """
    This function return the corresponding enum to the
    summary operator passed.

    Args:
        summary_operator : Type-str
    Returns:
        SummaryOperator enum member
    """
    if summary_operator == 'Sum':
        return enums.SummaryOperators.SUM
    elif summary_operator == 'Mean':
        return enums.SummaryOperators.MEAN
    elif summary_operator == 'Median':
        return enums.SummaryOperators.MEDIAN
    elif summary_operator == 'Count':
        return enums.SummaryOperators.COUNT
    elif summary_operator == 'Maximum':
        return enums.SummaryOperators.MAX
    elif summary_operator == 'Minimum':
        return enums.SummaryOperators.MIN
    elif summary_operator == 'Standard Deviation':
        return enums.SummaryOperators.STD
    elif summary_operator == 'Variance':
        return enums.SummaryOperators.VAR
    elif summary_operator == 'First':
        return enums.SummaryOperators.FIRST
    elif summary_operator == 'Last':
        return enums.SummaryOperators.LAST
    elif summary_operator == 'Count Distinct':
        return enums.SummaryOperators.DISTINCT
    elif summary_operator == 'Proportion of sum':
        return enums.SummaryOperators.PROPORTION_OF_SUM
    elif summary_operator == 'Proportion of count':
        return enums.SummaryOperators.PROPORTION_OF_COUNT
    else:
        return None



def _str_to_time_granularity_enum(time_granularity):
    """
    This function return the corresponding enum to the
    summary operator passed.

    Args:
        time_granularity : Type-str
    Returns:
        SummaryOperator enum member
    """
    if time_granularity == 'Annually':
        return enums.Granularities.ANNUALLY
    elif time_granularity == 'Monthly':
        return enums.Granularities.MONTHLY
    elif time_granularity == 'Daily':
        return enums.Granularities.DAILY
    elif time_granularity == 'Hourly':
        return enums.Granularities.HOURLY
    elif time_granularity == None:
        return None
    else:
        raise Exception('Granularity not supported')

def func(inp_json, change_list):
    for key in change_list.keys():
        inp_json[key] = change_list[key]

    return inp_json

def remove_empty_columns(query_table_dataframe):
    empty_header_present = False

    for column_name in list(query_table_dataframe.columns.values):
        if(column_name==""):
            empty_header_present = True
    
    if(empty_header_present):
        query_table_dataframe.drop(columns=[""])

    return query_table_dataframe


def remove_duplicate_named_columns(query_table_dataframe):
    #query_table_dataframe.columns.duplicated() gives a list of True and False for unique columns
    query_table_dataframe = query_table_dataframe.loc[:,~query_table_dataframe.columns.duplicated()]
    return query_table_dataframe    

def _get_value(dict, key):
    """
    Returns the value for corresponding key. If key is not present return None
    """
    if key in dict.keys():
        return dict[key]
    return None

def get_hardcoded_mean_vs_median_suggestion():
    suggestion = {}

    row_list = []
    row_list.append({'row':1, 'confidence_score':100})
    row_list.append({'row':2, 'confidence_score':100})

    suggestion['suggestion'] = 'Mean of rows are very different from Median at rows ' + str([row['row'] for row in row_list])
    suggestion['oversight_name'] = 'Mean vs Median'
    suggestion['is_row_level_suggestion'] = True
    suggestion['row_list'] = row_list

    change_list = {'summaryOperator':'Median'}
    suggestion['change_list'] = change_list

    return suggestion

def _list_all_dimensions_metrics(table, dimensions, metric):
    """
    This function return a tuple of all_dimensions and all_metrics

    Args:
        table: Type-pandan DataFrame
        dimensions: Type-list of strings
        metric: string
    Returns:
        Tuple of all_dimensions and all_metrics
    """

    num_rows = table.shape[0]

    all_dimensions = []
    all_metrics = []

    dimension_list = []
    if dimensions is not None:
        dimension_list = dimensions

    for column in table.columns:
        if column in dimension_list or metric == column:
            if column in dimension_list:
                all_dimensions.append(column)
            if metric == column:
                all_metrics.append(metric)
        else:
            is_metric = True
            for row_i in range(num_rows):
                if str(type(table.loc[row_i, column])) == "<class 'str'>":
                    is_metric = False
            if is_metric == True:
                all_metrics.append(column)
            else:
                all_dimensions.append(column)
    return (all_dimensions, all_metrics)

def _get_number_of_column_label(label):
    """
    This function returns a number which corresponds to the label.
    Example : 'A' -> 1 , 'Z' -> 26 , 'AA' -> 27 , 'BA' -> 53

    Args : 
        label : Type-str
            Denotes the label given to the column by sheets
    Returns :
        num : Type-int
            Denotes the numbering of columns(1-indexed)

    """

    num = 0
    power_of_26 = 1

    for i in range(len(label)-1,-1,-1):
        value = ord(label[i]) - ord('A') + 1

        num += power_of_26*value

        power_of_26 = 26*power_of_26

    return num

def _get_label_from_number(num):
    """
    This function returns the label associated with the corresponding number
    Example : 1 -> 'A' , 26 -> 'Z' , 27 -> 'AA' , 53 -> 'BA'

    Args : 
        num : Type-int
            Denotes the numbering of columns(1-indexed)
    Returns :
        label : Type-str
            Denotes the label given to the column by sheets

    """

    label = ''

    while(num > 0):
        x = num % 26

        if x == 0 :
            label += 'Z'
            num //= 26
            num -= 1
        else :
            label += chr(x + ord('A') - 1)
            num //= 26

    return label[::-1]

def _get_all_column_labels(rangeA1Notation):
    """
    This function returns a list which gives all the column labels present in the table

    Args:
        rangeA1Notation : Type-str
                          Denotes the data range selected by user. 
                          Example : "A1:C18" , "AA1:CC33"
    Returns:
        List of all column labels where data is present.
        Example : ['A','B','C']
    """

    starting_col = ""
    ending_col = ""

    starting_column_filled = False

    for c in rangeA1Notation :
        if c.isalpha():
            if not starting_column_filled :
                starting_col += c
            else :
                ending_col += c
        else:
            starting_column_filled = True

    list_of_column_labels = []

    starting_col_label_number = _get_number_of_column_label(starting_col)
    ending_col_label_number = _get_number_of_column_label(ending_col)

    for label_number in range(starting_col_label_number, ending_col_label_number + 1) :
        list_of_column_labels.append(_get_label_from_number(label_number))

    return list_of_column_labels

def _get_all_row_labels(rangeA1Notation):
    """
    This function returns a list which gives all the row labels present in the table

    Args:
        rangeA1Notation : Type-str
                          Denotes the data range selected by user. 
                          Example : "A1:C18" , "AA1:CC33"
    Returns:
        List of all column labels where data is present.
        Example : [1,2,3,4,5,...,17,18]
    """

    starting_row = ""
    ending_row = ""

    starting_row_filled = False

    for c in rangeA1Notation: 
        if c.isnumeric():
            if not starting_row_filled :
                starting_row += c
            else :
                ending_row += c
        elif c == ':' :
            starting_row_filled = True

    list_of_row_labels = []

    for label_number in range(int(starting_row) + 1 , int(ending_row) + 1):
        list_of_row_labels.append(label_number) 

    return list_of_row_labels

def _get_cheader_to_clabel(table, all_column_labels): 
    """ 
    This function returns a dictionary mapping all column headers to their respective
    column label.

    Args:
        table : Type-Pandas dataframe
            Contents of the sheets
        all_column_lables : Type-list of str
            Contains all column labels in same order as column headers
    Returns:
        Dictionary with (key,value) where key is column header 
        and value is the respective column label
    """

    cheader_to_clabel = {}

    for i in range(len(all_column_labels)) :
        cheader_to_clabel[table[0][i]] = all_column_labels[i]

    return cheader_to_clabel
