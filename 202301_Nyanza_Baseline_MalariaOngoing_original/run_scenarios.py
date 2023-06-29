import itertools
import numpy as np
import os
import pandas as pd
import sys
import time

from calibtool.CalibManager import CalibManager
from calibtool.ParameterSet import ParameterSet, NaNDetectedError

from dtk.utils.builders.TemplateHelper import TemplateHelper
from dtk.utils.core.DTKConfigBuilder import DTKConfigBuilder
from simtools.Analysis.AnalyzeManager import AnalyzeManager
from simtools.Analysis.BaseAnalyzers.DownloadAnalyzerTPI import DownloadAnalyzerTPI
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.ModBuilder import ModBuilder
from simtools.SetupParser import SetupParser
from simtools.Utilities.Initialization import load_config_module

from hiv.utils.utils import add_post_channel_config_as_asset

SetupParser.default_block = 'NYUCLUSTER'

RESAMPLING_METHODS_STR = ', '.join(['roulette', 'provided'])
DEFAULT_N_SAMPLES = 300
DEFAULT_BLOCK = 'NYUCLUSTER'
DEFAULT_OUTPUT_DIR = 'Calibrated_RSA_Scenarios'
DEFAULT_DOWNLOAD_FILES = os.path.join('output', 'ReportHIVByAgeAndGender.csv')

SCENARIO_TABLE_MODE = 'scenario_table'
SCENARIO_TEMPLATE_SETS_MODE = 'scenario_template_sets'

TPI_TAG = 'parameterization_id'
REP_TAG = 'Run_Number'

DEFAULT_CAMPAIGN = 'Default_Campaign'


class UnknownResampleMethodException(Exception):
    pass


class MissingCampaignSpecificationException(Exception):
    pass


DOLPHIN = '''
                                  _
                             _.-~~.)
       _.--~~~~~---....__  .' . .,' 
     ,'. . . . . . . . . .~- ._ (
    ( .. .g. . . . . . . . . . .~-._
 .~__.-~    ~`. . . . . . . . . . . -. 
 `----..._      ~-=~~-. . . . . . . . ~-.  
           ~-._   `-._ ~=_~~--. . . . . .~.  
            | .~-.._  ~--._-.    ~-. . . . ~-.
             \ .(   ~~--.._~'       `. . . . .~-.                ,
              `._\         ~~--.._    `. . . . . ~-.    .- .   ,'/
 . _ . -~\        _ ..  _          ~~--.`_. . . . . ~-_     ,-','`  .
           ` ._           ~                ~--. . . . .~=.-'. /. `
     - . -~            -. _ . - ~ - _   - ~     ~--..__~ _,. /   \  -
             . __ ..                   ~-               ~~_. (  `
  _ _               `-       ..  - .    . - ~ ~ .    \    ~-` ` `  `.
                                               - .  `  .   \  \ `. 
'''


def load_templates(loaded_module):
    # perform any template updates for generic scenario running
    for scenario_name, scenario_templates in loaded_module.run_calib_args['scenario_template_sets'].items():
        for template in scenario_templates['config']:
            template.set_param("Enable_Demographics_Builtin", 0, allow_new_parameters=True)


# These are two methods for traversing nested python structures of lists/dicts and converting strings representing lists
# to actual lists. e.g. {'somekey': {'a': 4, 'b': '[1,2,3]'}} => {'somekey': {'a': 4, 'b': [1,2,3]}}
def check_recurse(item, indexer):
    if isinstance(item[indexer], str):
        if '[' in item[indexer]:
            item[indexer] = eval(item[indexer])
    else:
        find_and_eval(item[indexer])


def find_and_eval(item):
    if isinstance(item, list):
        for index in range(len(item)):
            check_recurse(item, index)
    elif isinstance(item, dict):
        keys = item.keys()
        for key in keys:
            check_recurse(item, key)
    else:
        pass  # do nothing


def build_and_run_simulations(samples, scenario_template_sets, scenario_param_dicts, suite_name, loaded_module):
    # Create the default config builder
    config_builder = DTKConfigBuilder()

    # This is REQUIRED by the template
    config_builder.ignore_missing = True

    # Adding the post_channel_config.json upload to Assets/ to allow post-processing of scenario sims to occur
    reference_info = loaded_module.run_calib_args['reference_info']
    add_post_channel_config_as_asset(config_builder, reference_info['channels'],
                                     reference_info['reference'], reference_info['site_info'])

    experiment_managers = []  # All the experiment managers for all experiments

    # Create a suite to hold all the experiments
    suite_id = None # create_suite(suite_name)

    # Create the scenarios
    for template_set_name, scenario_template_set in scenario_template_sets.items():
        # available_campaigns = scenario_template_set.pop('campaign')  # we will add the selected campaign back in later
        # generate one experiment per template_set X scenario_params combination
        for scenario_params in scenario_param_dicts:
            # Determine which campaign file to use as the campaign template for this scenario
            campaign_template_name = scenario_params.pop('Campaign', None)
            resolved_scenario_template_set = loaded_module.resolve_scenario_template_set(template_set_name=template_set_name,
                                                                                         campaign_template_name=campaign_template_name)

            # campaign_template = _get_campaign_template(campaign_template_name=campaign_template_name,
            #                                            scenario_name=scenario_params['Scenario'],
            #                                            available_campaigns=available_campaigns)

            # name the scenario (experiment) by combining the template set name and provided Scenario name
            sn = scenario_params.pop('Scenario', 'DefaultScenario')
            campaign_string = os.path.splitext(campaign_template_name)[0] if campaign_template_name else DEFAULT_CAMPAIGN
            if sn is None:
                scenario_name = '-'.join([template_set_name, campaign_string])
            else:
                scenario_name = '-'.join([template_set_name, campaign_string, sn])

            print('Scenario: %s Using template set: %s' % (scenario_name, template_set_name))

            # map the sample parameters to model parameters
            mapped_sample_params = []
            for sample in samples:
                mapped = loaded_module.map_sample_to_model_input(sample_dict=sample.param_dict,
                                                                 template_set_name=template_set_name,
                                                                 scenario_name=scenario_name,
                                                                 campaign_filename=campaign_template_name,
                                                                 random_run_number=False)

                # for tracking which parameterization & run number is which sim/result
                mapped[REP_TAG] = sample.run_number
                mapped[TPI_TAG] = sample.parameterization_id

                mapped_sample_params.append(mapped)

            # Combine scenario name and scenario table parameters with sample param dicts
            combined_params = []
            for sample in mapped_sample_params:
                current = {}
                current.update(sample)
                current.update(scenario_params)
                current.update({'Config_Name': scenario_name, REP_TAG: current[REP_TAG]})

                # including parameterization id number (TPI) and run number as tags
                if 'TAGS' not in current:
                    current['TAGS'] = {}

                parameterization_id = current.pop(TPI_TAG)
                current['TAGS'].update({TPI_TAG: parameterization_id, REP_TAG: current[REP_TAG]})
                combined_params.append(current)

            # Extract the headers - replacing "well known" prefixes as needed
            headers = [k.replace('CONFIG.', '').replace('DEMOGRAPHICS.', '').replace('CAMPAIGN.', '') for k in
                       combined_params[0].keys()]

            # Construct the table
            table = [list(c.values()) for c in combined_params]

            # Initialize the template & create the experiment builder
            tpl = TemplateHelper()
            tpl.set_dynamic_header_table(headers, table)
            tpl.active_templates = list(itertools.chain(*resolved_scenario_template_set.values()))

            experiment_builder = ModBuilder.from_combos(tpl.get_modifier_functions())

            experiment_manager = ExperimentManagerFactory.from_cb(config_builder)
            suite_id = suite_id or experiment_manager.create_suite(suite_name=suite_name)
            experiment_manager.run_simulations(exp_name=scenario_name, exp_builder=experiment_builder,
                                               suite_id=suite_id)
            experiment_managers.append(experiment_manager)

    return experiment_managers


def analyze_experiments(experiment_managers, output_path, suite_id, download_filenames):
    # if suite_id was provided AND our block type is CLUSTER, we will not wait but just download.

    # Download (analyze) files for experiments as they finish up.
    while not all([em.finished() for em in experiment_managers]):
        print("Waiting 60 seconds for experiments to complete...")
        sys.stdout.flush()
        time.sleep(60)
        [e.refresh_experiment() for e in experiment_managers]
    
    print('Experiments complete, downloading...')
    am = AnalyzeManager(verbose=False)
    for em in experiment_managers:
        print(em.experiment.simulations)
        am.add_experiment(em.experiment)
    am.add_analyzer(DownloadAnalyzerTPI(filenames=download_filenames,
                                        output_path=output_path,
                                        TPI_tag=TPI_TAG,
                                        REP_tag=REP_TAG))
    print(am.analyzers)
    print(am.simulations)
    am.analyze()


def load_scenario_table(filename):
    # returns a list of parameter dicts, one for each scenario (scenario table row)
    if filename is not None:
        scenario_table = pd.read_csv(filename)
        if 'Campaign' not in scenario_table.columns:
            raise MissingCampaignSpecificationException('Column \'Campaign\' is missing from %s if used' % filename)
        scenario_param_dicts = scenario_table.to_dict(orient='records')
        find_and_eval(scenario_param_dicts)  # convert any strings representing lists to actual python lists
    else:
        scenario_param_dicts = [{'Scenario': None, 'Campaign': None}]
    return scenario_param_dicts


def set_parameterization_ids(samples):
    for index in range(len(samples)):
        samples[index].parameterization_id = index
    return samples


def get_samples(args):
    resample_method = args.resample_method.lower()

    if resample_method == 'provided':
        # the provided csv files needs to be in the exact same format at dumped into resampled_parameter_sets.csv below
        samples = pd.read_csv(args.samples_file)
        sample_dicts = samples.to_dict(orient='records')
        try:
            samples = [ParameterSet.from_dict(d) for d in sample_dicts]
        except NaNDetectedError as e:
            e.args = (f"One or more blank entries or lines found in samples file {args.samples_file} . "
                      f"Please fix/remove them. Enjoy this dolphin.\n{DOLPHIN}",)
            raise e
    else:
        if resample_method == 'roulette':
            # obtain existing samples and their likelihoods
            calib_manager = CalibManager.open_for_reading(args.calibration_dir)
            parameter_sets = calib_manager.get_parameter_sets_with_likelihoods()
            sorted_parameter_sets = sorted(parameter_sets, key=lambda ps: ps.likelihood_exponentiated,
                                           reverse=True)
            # determine distribution of top and probabilistically selected samples
            n_top_samples = int(np.ceil(args.n_samples / 3))
            n_roulette_samples = args.n_samples - n_top_samples

            # select the top samples - sorted_parameter_sets is sorted most<->least likely
            top_samples = sorted_parameter_sets[0:n_top_samples]

            # remove selected "top" samples and roulette sample the remaining to prevent duplication
            remaining_sorted_parameter_sets = sorted_parameter_sets[n_top_samples:-1]

            # normalize the parameter set likelihoods for probabilistic selection
            total_likelihood = sum([ps.likelihood_exponentiated for ps in remaining_sorted_parameter_sets])
            p = [ps.likelihood_exponentiated / total_likelihood for ps in remaining_sorted_parameter_sets]

            # probabilistically select the remaining samples - duplicates of top_samples are allowed
            roulette_samples = list(np.random.choice(remaining_sorted_parameter_sets, p=p, size=n_roulette_samples, replace=False))

            samples = top_samples + roulette_samples
        else:
            raise UnknownResampleMethodException('Unknown resample method: %s' % resample_method)

        # for readable logging purposes
        samples = set_parameterization_ids(samples)

        # note that we are not re-writing this file if resample_method == 'provided'
        samples_df = pd.DataFrame(data=[s.to_dict() for s in samples])
        samples_df.to_csv('resampled_parameter_sets.csv', index=False)

    return samples


def main(args):
    if args.suite_id:
        if SetupParser.get('type') == 'CLUSTER':
            from simtools.Utilities.ClusterUtilities import exps_for_suite_id
        else:
            from simtools.Utilities.COMPSUtilities import exps_for_suite_id
        from simtools.Utilities.Experiments import retrieve_experiment

        # do not run new scenarios. Get experiment managers to facilitate download only, instead.
        experiments = exps_for_suite_id(args.suite_id)
        experiments = [retrieve_experiment(e.id) for e in experiments]
        experiment_managers = [ExperimentManagerFactory.from_experiment(experiment=exp) for exp in experiments]
        if SetupParser.get('type') == 'CLUSTER':
            for em in experiment_managers:
                em.wait_for_finished()
    else:
        # load scenario information
        load_templates(args.loaded_module)

        # load scenario table if needed - returns a virtually blank dataframe if no load was necessary
        scenario_param_dicts = load_scenario_table(filename=args.scenario_table)

        # now determine the samples to use as the basis for each scenario
        samples = get_samples(args)

        # now run the samples X scenarios simulations
        experiment_managers = build_and_run_simulations(samples,
                                                        scenario_template_sets=args.loaded_module.run_calib_args['scenario_template_sets'],
                                                        scenario_param_dicts=scenario_param_dicts,
                                                        suite_name=args.suite_name,
                                                        loaded_module=args.loaded_module)
    if not args.no_download:
        analyze_experiments(experiment_managers, output_path=args.output_path, suite_id=args.suite_id, download_filenames=args.download_filenames)
    print('Done!')


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--calib-dir', dest='calibration_dir', type=str, default=None,
                        help='Directory of calibration to resample (Required for resampling method \'roulette\')).')
    parser.add_argument('-c', '--calib-script', dest='calibration_script', type=str, required=True,
                        help='Script used to run the calibration (Required).')
    parser.add_argument('-m', '--resample-method', dest='resample_method', type=str, required=True,
                        help='Resampling methodology to use (Required) (Valid: %s)' % RESAMPLING_METHODS_STR)

    parser.add_argument('--samples', dest='samples_file', type=str, default=None,
                        help='csv file with user-defined samples to use (Required for resampling method \'provided\')')

    parser.add_argument('-n', '--nsamples', dest='n_samples', type=int, default=DEFAULT_N_SAMPLES,
                        help='Number of resampled parameter sets to generate and use (Default: %d) '
                             '(Not valid with resampling method \'provided\'.' % DEFAULT_N_SAMPLES)
    parser.add_argument('-o', '--output-dir', dest='output_path', type=str, default=DEFAULT_OUTPUT_DIR,
                        help='Directory to hold scenario output files (Default: %s).'
                             % DEFAULT_OUTPUT_DIR)
    parser.add_argument('-f', '--files', dest='download_filenames', type=str, default=DEFAULT_DOWNLOAD_FILES,
                        help='Filenames to retrieve from scenario simulations (if downloading). Paths relative to simulation directories. Comma-separated list if more than one (Default: %s)' % DEFAULT_DOWNLOAD_FILES)
    parser.add_argument('--no-download', dest='no_download', action='store_true',
                        help='Do not download files after running scenarios (Default: download files).')
    parser.add_argument('-s', '--suite-name', dest='suite_name', type=str, required=True,
                        help='Name of suite for scenario experiment to be run (Required).')
    parser.add_argument('--table', dest='scenario_table', type=str, default=None,
                        help='Scenarios will be generated using a csv table file (mutually exclusive with --template-sets).')
    parser.add_argument('--template-sets', dest='template_sets', action='store_true',
                        help='Scenarios will be generated using template sets (mutually exclusive with --table).')
    parser.add_argument('-id', dest='suite_id', type=str, default=None,
                        help='ID of existing scenarios suite to download. Will not run scenarios (Default: run scenarios.)')
    parser.add_argument('-b', '--block', dest='selected_block', type=str, default=DEFAULT_BLOCK,
                        help='simtools.ini block to use (Default: %s)' % DEFAULT_BLOCK)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    script_args = parse_args()
    SetupParser.init(selected_block=script_args.selected_block)

    # making sure arguments related to template-set vs table scenario generation are configured properly
    if not ((script_args.scenario_table is None) ^ (script_args.template_sets is False)):
        raise Exception('Must either specify --table FILENAME or --template-sets for scenario generation.')

    if script_args.scenario_table is not None:
        script_args.scenario_mode = SCENARIO_TABLE_MODE
    else:
        script_args.scenario_mode = SCENARIO_TEMPLATE_SETS_MODE

    script_args.loaded_module = load_config_module(script_args.calibration_script)

    n_template_sets = len(script_args.loaded_module.scenario_template_sets)
    if n_template_sets == 0:
        raise Exception('Cannot proceed with zero template sets in provided calibration script.')

    if script_args.scenario_mode == SCENARIO_TABLE_MODE:
        if n_template_sets > 1:
            raise Exception('Exactly one template set (Baseline) must be specified in provided calibration script. There are %d.' % n_template_sets)

    if script_args.resample_method == 'provided':
        if script_args.samples_file is None:
            raise Exception('A csv file of samples must be provided via --samples when using resampling method \'provided\'.')
        if script_args.calibration_dir is not None:
            raise Exception('-d CALIB_DIR is not compatible with for resampling method \'provided\'')
    else:
        if script_args.samples_file is not None:
            raise Exception('--samples is only compatible with resampling method \'provided\'.')
        if script_args.calibration_dir is None:
            raise Exception('-d CALIB_DIR is required for resampling method \'roulette\'')


    script_args.download_filenames = script_args.download_filenames.strip().split(',')

    main(script_args)
