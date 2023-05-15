#!/usr/bin/python

from __future__ import print_function

import json
import os
import pandas as pd
import time
import math

# Relative to DTK output folder:
# from dtk.utils.observations.AgeBin import AgeBin


class UndefinedChannelException(Exception): pass


ByAgeAndGender_filename     = "ReportHIVByAgeAndGender.csv"
Calibration_filename        = "Calibration.json"

AGGREGATED_NODE = 0 # reserved node number for aggregated aka 'National' processing

OUTPUT_DIRECTORY = 'output'

MALE = 0
FEMALE = 1
BOTH = 2
GENDER_MAP = {'Male': MALE, 'Female': FEMALE, 'Both': BOTH}  # str to int
GENDER_STR = {k: v for v, k in GENDER_MAP.items()}  # int to str

# load file post_channel_config.json
ref_config = json.load(open(os.path.join("..","Assets", "post_channel_config.json"), 'rb'))


def timing(f, message):
    if message is not None:
        print('\r' + message, end='')
    t_start = time.clock()
    result = f()
    t_end = time.clock()
    if message is not None:
        print('{0:>10f}'.format(t_end-t_start))

    return result


def get_year(channel):
    return ref_config[channel]['Year']


def get_age_bin(channel):
    """
    tuple(15, 20) got written to [15, 20] in file post_channel_config.json
    here we just change [15, 20] back to (15, 20)
    """

    age_bins = ref_config[channel]['AgeBin']
    age_bins = [(g[0], g[1]) for g in age_bins]
    return age_bins


def get_gender(channel):
    genders = ref_config[channel]['Gender']
    genders = [GENDER_MAP[g] for g in genders]
    return genders


def get_reports(data):
    # verify channels
    channels_supported = ['Prevalence', 'Population', 'OnART', 'Incidence', 'ARTCoverage']#,'CMDPrevalence']
    channels_ref = list(ref_config.keys())

    channels_not_supported = list(set(channels_ref) - set(channels_supported))
    if(len(channels_not_supported)) > 0:
        raise UndefinedChannelException('No definition for how to post-process channel: %s' % channels_not_supported[0])

    # add details for each channel
    entries = []

    first_year = int(math.ceil(data.Year.min()))
    last_prevalence_year = int(data.Year.max())
    last_incidence_year = last_prevalence_year - 1

    channel = 'Prevalence'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Prevalence',
                 'Year': set(list(range(first_year, last_prevalence_year + 1)) + get_year(channel=channel)),
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': lambda row: float(row.Infected) / float(row.Population) if row.Population > 0 else 0}
        entries.append(entry)

    channel = 'Population'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Prevalence',
                 'Year': set(list(range(first_year, last_prevalence_year + 1)) + get_year(channel=channel)),
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': lambda row: row.Population}
        entries.append(entry)

    channel = 'OnART'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Prevalence',
                 'Year': set([x + 0.5 for x in range(2000,   last_prevalence_year)] + get_year(channel=channel)),
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': lambda row: row.On_ART}
        entries.append(entry)

    channel = 'Incidence'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Incidence',
                 'Year': set(list(range(first_year, last_incidence_year + 1)) + get_year(channel=channel)),  # must be integers
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': compute_incidence}
        entries.append(entry)

    channel = 'ARTCoverage'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Prevalence',
                 'Year': set(list(range(first_year, last_prevalence_year + 1)) + get_year(channel=channel)),
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': lambda row: float(row.On_ART) / float(row.Infected) if row.Infected > 0 else 0}
        entries.append(entry)

    channel = 'ARTCoverage'
    if channel in channels_ref:
        entry = {'Name': channel,
                 'Type': 'Prevalence',
                 'Year': set(list(range(first_year, last_prevalence_year + 1)) + get_year(channel=channel)),
                 'AgeBins': get_age_bin(channel=channel),
                 'Gender': get_gender(channel=channel),
                 'ByNode': 'Both',
                 'Map': lambda rows: rows.sum(),
                 'Reduce': lambda row: float(row.On_ART) / float(row.Infected) if row.Infected > 0 else 0}
        entries.append(entry)

    # channel = 'CMDPrevalence'
    # if channel in channels_ref:
    #     entry = {'Name': channel,
    #              'Type': 'Prevalence',
    #              'Year': set(list(range(first_year, last_prevalence_year + 1)) + get_year(channel=channel)),
    #              'AgeBins': get_age_bin(channel=channel),
    #              'Gender': get_gender(channel=channel),
    #              'ByNode': 'Both',
    #              'Map': cmd_prevalence_map, # see below
    #              'Reduce': lambda row: float(row.CMD_population) / float(row.Population) if row.Population > 0 else 0}
    #     entries.append(entry)
        

    return entries

def cmd_prevalence_map(rows):
    cmd_population = rows[rows['IP_Key:CMDStatus'] == 'CMD_pos'].sum()['Population']  # number of ppl with CMD
    mapped_row = rows.sum()  # gives us summed values, e.g. of Population, regardless of CMD status
    mapped_row['CMD_population'] = cmd_population
    return mapped_row


def compute_incidence(row):
    newly_infected_annualized = float(row.newly_infected_annualized)
    if row.Population > 0:
        incidence = newly_infected_annualized / float(row.Population - row.Infected - row.Newly_Infected)
    else:
        incidence = 0
    print('%s = %s / (%s - %s - %s)' % (incidence, newly_infected_annualized, row.Population, row.Infected, row.Newly_Infected))
    return incidence


def add_year_in(df):
    """
    Determine the year a particular date/timeframe occurred in (assumes tail-end dates).
    For use in 'E'-type sheets.
    """
    import numpy as np
    year_in = np.ceil(df['Year']) - 1
    return df.assign(year_in=year_in)


def preprocess_for_incidence(all_data):
    input_stratifiers = ['Year', 'NodeId', 'Gender', 'Age', 'IsCircumcised', 'IP_Key:Risk']
    grouping_stratifiers = ['NodeId', 'Gender', 'Age', 'year_in', 'IsCircumcised', 'IP_Key:Risk']

    # add the year each row is in
    data = add_year_in(all_data)
    data = data[list(set(input_stratifiers + ['year_in', 'Year', 'Newly_Infected', 'Infected', 'Population']))]

    # yearly incidence count, reported on 0.5 year to line up with the data it will be combined with in a calculation
    summed = data.drop('Year', axis=1)
    summed = summed.groupby(grouping_stratifiers).sum().reset_index()[grouping_stratifiers + ['Newly_Infected']]
    summed = summed.assign(year_in=summed['year_in'] + 0.5)
    summed = summed.rename(columns={'year_in': 'Year', 'Newly_Infected': 'newly_infected_annualized'})

    # merge into original dataframe
    summed = summed.set_index(input_stratifiers)
    data = data.set_index(input_stratifiers)
    data = data.merge(summed, how='inner', left_index=True, right_index=True).reset_index()

    # convert back to integer year; this is needed to report results on integer years as requested
    data = data.drop('Year', axis=1)
    data = data.rename(columns={'year_in': 'Year'})

    # drop circum. column; only because we added it
    data = data.drop('IsCircumcised', axis=1)
    data = data.drop('IP_Key:Risk', axis=1)
    return data


def get_blank_dataframe():
    output_stratifiers = ['Year', 'Node', 'Gender', 'AgeBin']
    output = pd.DataFrame(columns=(output_stratifiers + ['Result']))
    return output


def process_nodes(data, output, year, gender, min_age, max_age, report, node_ids):
    print('channel: %s year: %s node_ids: %s' % (report['Name'], year, node_ids))
    for node_id in node_ids:
        # determine which data lines need to be included in this calculation
        conditions = (data.Year == year) & (data.Age >= min_age) & (data.Age < max_age)
        if gender != BOTH:
            conditions = conditions & (data.Gender == gender)
        if node_id != AGGREGATED_NODE:
            conditions = conditions & (data.NodeId == node_id)

        rows = data[conditions]

        if len(rows) == 0:
            raise Exception('Channel %s data is empty for year: %s. Something went wrong, ask a developer.' %
                            (report['Name'], year))

        mapping = timing(lambda: report['Map'](rows), message=None)  # sum data
        try:
            result = report['Reduce'](mapping)
        except AttributeError:
            print(' -- FAILED!')
            return output
        new_row = {'Year': year, 'Node': node_id, 'Gender': GENDER_STR[gender], 'AgeBin': '[%d:%d)' % (min_age, max_age), 'Result': result}
        output = output.append(new_row, ignore_index=True)
    return output

def process_report(report, all_data, node_ids):
    # preprocessing for incidence types
    if report['Type'] == 'Incidence':
        data = preprocess_for_incidence(all_data)
    else:
        data = all_data

    # determine which type(s) of processing to do
    process_by_node = True if report['ByNode'] in [True, 'Both'] else False
    process_aggregated = True if report['ByNode'] in [False, 'Both'] else False

    # Create output data
    output = get_blank_dataframe()
    for year in report['Year']:
        for gender in report['Gender']:
            for min_age, max_age in report['AgeBins']:
                if process_by_node:
                    output = process_nodes(data, output, year, gender, min_age, max_age, report,
                                           node_ids=node_ids)

                if process_aggregated:
                    output = process_nodes(data, output, year, gender, min_age, max_age, report,
                                           node_ids=[AGGREGATED_NODE])

    output.set_index(['Year', 'Node', 'Gender', 'AgeBin'], inplace=True)
    return output


def main(output_dir):
    print("Hello from Python!")
    print("Started Python post processing  @ " + time.asctime())
    print("Current working directory is: " + os.getcwd())

    filename = os.path.join(output_dir, ByAgeAndGender_filename)
    if not os.path.isfile(filename):
        print("!!!! Can't open " + filename + "!")
        return

    print('Loading file: %s' % filename)
    data = timing(lambda: pd.read_csv(filename), message='Load data:    ')

    reports = get_reports(data)

    data.columns = map(lambda s: s.strip().replace(' ', '_').replace('(', '').replace(')', ''), data.columns)
    node_ids = sorted([int(node_id) for node_id in data.NodeId.unique()])

    post_process_dir = 'post_process'
    directory = os.path.join(output_dir, post_process_dir)
    if not os.path.exists(directory):
        os.makedirs(directory)

    for report in reports:
        result = timing(lambda: process_report(report, data, node_ids), message=report['Name'])
        result.to_csv(os.path.join(output_dir, post_process_dir, '%s.csv' % report['Name']))

    print("Finished Python post processing @ " + time.asctime())


application = main

if __name__ == '__main__':
    main(OUTPUT_DIRECTORY)
