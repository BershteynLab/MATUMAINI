import copy
import itertools
import math
import numpy as np
import os
import random
import re
from scipy.special import gammaln  # for calculation of mu_r

from calibtool.algorithms.OptimTool import OptimTool
from calibtool.CalibManager import CalibManager
from calibtool.plotters.LikelihoodPlotter import LikelihoodPlotter
from calibtool.plotters.OptimToolPlotter import OptimToolPlotter
from calibtool.plotters.SiteDataPlotter import SiteDataPlotter

from calibtool.resamplers.CramerRaoResampler import CramerRaoResampler
from calibtool.resamplers.RandomPerturbationResampler import RandomPerturbationResampler
from dtk.utils.builders.ConfigTemplate import ConfigTemplate
from dtk.utils.builders.TemplateHelper import TemplateHelper
from dtk.utils.builders.TaggedTemplate import DemographicsTemplate
from dtk.utils.core.DTKConfigBuilder import DTKConfigBuilder
from dtk.utils.observations.utils import parse_ingest_data_from_xlsm
from simtools.SetupParser import SetupParser

from hiv.analysis.HIVCalibSite import HIVCalibSite
from hiv.utils.utils import make_campaign_template, add_post_channel_config_as_asset

def load_campaign_templates(template_dir):
    # Finds and loads all campaign files in the specified directory, returning a {filename: template} filled dict
    campaign_file_regex = re.compile("^campaign_.+\.json$")
    campaign_templates = {}
    for filename in os.listdir(template_dir):
        if campaign_file_regex.match(filename) is not None:
            full_filename = os.path.join(template_dir, filename)
            campaign_template = make_campaign_template(base_campaign_filename=full_filename)
            campaign_template.set_params(static_params)
            campaign_templates[filename] = campaign_template
    return campaign_templates

SetupParser.default_block = "NYUCLUSTER"

# calibration will be performed using the scenario_template_set that is loaded and given this name (see below)
CALIBRATION_SCENARIO = 'Baseline'

# commonly modified calibration variables
 # For quick test simulations, BASE_POPULATION_SCALE_FACTOR is set to a very low value. 
 # 0.005 for testing. Use 0.2 for full calibration
 # I (David) has found that 0.02 can lead to the epidemic never taking off in some counties for Nyanza
BASE_POPULATION_SCALE_FACTOR = 0.2
N_ITERATIONS = 1
N_SAMPLES_PER_ITERATION = 20  # the number of distinct parameter sets to run per iteration
N_REPLICATES = 3  # replicates > 1 helps OptimTool to be more stable at the cost of more simulations. 3 is recommended.
TEST_N = '3'  # TEST_N is macro variable used to create directory name

# The excel file with parameter, analyzer, and reference data to parse
ingest_xlsm_filename = os.path.join('Data', 'calibration_ingest_form_Nyanza.xlsm')

# params is a dict, site_info is a dict, reference is a PopulationObs object, analyzers is a list of dictionaries of
# analyzer arguments
params, site_info, reference, analyzers, channels = parse_ingest_data_from_xlsm(filename=ingest_xlsm_filename)
# making this available to any script that imports this file as a module, like run_scenarios.py
reference_info = {
    'params': params,
    'site_info': site_info,
    'reference': reference,
    'analyzers': analyzers,
    'channels': channels
}

# This is now generic and is part of the HIV repository. Any local site python file is unnecessary and will be unused.
site = HIVCalibSite(analyzers=analyzers, site_data=site_info, reference_data=reference, force_apply=True)

# dtk analyze compatibility
analyzers = site.analyzers

plotters = [
    LikelihoodPlotter(),
    OptimToolPlotter()
]

province_names = list(site_info['node_map'].values())

static_params = {'x_Base_Population': BASE_POPULATION_SCALE_FACTOR}

# Setting up our model configuration from templates
# There must be at least ONE entry in the scenario_template_sets dictionary: Baseline
# The Baseline template set will be used for calibration.
# The only reason for including additional template sets in scenario_template_sets is if you wish to run scenarios
# later on with run_scenarios.py and wish to use multiple templates sets (one per scenario) instead of the csv
# table style of scenario generation.
scenario_template_sets = {}

dir_path = os.path.dirname(os.path.realpath(__file__))

template_files_dir = os.path.join(dir_path, 'InputFiles', 'Templates')
static_files_dir = os.path.join(dir_path, 'InputFiles', 'Static')

# Defining the base calibration scenario
config_templates = []
config_filename = os.path.join(template_files_dir, 'config.json')
cfg = ConfigTemplate.from_file(config_filename)
cfg.set_params(static_params)
config_templates.append(cfg)

# This returns a dictionary filled with file_basename: campaign_template items
campaign_templates = load_campaign_templates(template_dir=template_files_dir)

demographics_templates = []
demographics_filenames = [
    os.path.join(static_files_dir, 'Demographics.json'),
    os.path.join(template_files_dir, 'PFA_Overlay.json'),
    os.path.join(template_files_dir, 'Accessibility_and_Risk_IP_Overlay.json'),
    os.path.join(template_files_dir, 'Risk_Assortivity_Overlay.json')
]
for filename in demographics_filenames:
    template = DemographicsTemplate.from_file(filename)
    demographics_templates.append(template)

configuration_templates = {
    'config': config_templates,
    'campaign': campaign_templates,
    'demographics': demographics_templates
}

# If you intend to run template-set-based scenarios in addition to the one used for calibration (your 'baseline'),
# you will eventually need to define additional entries in scenario_template_sets
scenario_template_sets[CALIBRATION_SCENARIO] = configuration_templates


def resolve_scenario_template_set(template_set_name, campaign_template_name):
    # This is required to generate a flat list of templates with the desired campaign template, as there could well be
    # more than one of them in the 'campaign' dict
    active_templates = copy.deepcopy(scenario_template_sets[template_set_name])
    campaign_templates = active_templates.pop('campaign')
    if campaign_template_name is None:  # grab the one and only campaign file, error if > 1 of them
        n_campaign_templates = len(campaign_templates)
        if n_campaign_templates != 1:
            raise Exception('There must be exactly one campaign template in template set: %s. There are %d .' % (template_set_name, n_campaign_templates))
        active_templates['campaign'] = list(campaign_templates.values())  # only one of them, we checked
    else:
        campaign_template = campaign_templates.get(campaign_template_name, None)
        if campaign_template is not None:
            active_templates['campaign'] = [campaign_template]
        else:
            raise Exception('Unknown campaign specified: %s' % campaign_template_name)
    return active_templates


def base_table_for_scenario(template_set_name, scenario_name, campaign_filename):
    active_templates = resolve_scenario_template_set(template_set_name=template_set_name,
                                                     campaign_template_name=campaign_filename)
    base_table = {
        'ACTIVE_TEMPLATES': list(itertools.chain(*active_templates.values())),
        'TAGS': {'Scenario': scenario_name, 'pyOptimTool': None}
    }
    return base_table


config_builder = DTKConfigBuilder()
config_builder.ignore_missing = True

# generate channel config as an asset
add_post_channel_config_as_asset(config_builder, channels, reference, site_info)


def constrain_sample(sample):
    if ('PrExTrnsMaleLOW' in sample) and ('PrExTrnsMaleMED' in sample):
        sample['PrExTrnsMaleLOW'] = min(sample['PrExTrnsMaleLOW'], sample['PrExTrnsMaleMED'])
    if ('PrExTrnsFemLOW' in sample) and ('PrExTrnsFemMED' in sample):
        sample['PrExTrnsFemLOW'] = min(sample['PrExTrnsFemLOW'], sample['PrExTrnsFemMED'])
    return sample


def map_sample_to_model_input_fn(config_builder, sample_dict, scenario_name=CALIBRATION_SCENARIO):
    # for calibration use, only
    templates = TemplateHelper()
    table = map_sample_to_model_input(sample_dict, template_set_name=CALIBRATION_SCENARIO, scenario_name=scenario_name,
                                      campaign_filename=None)  # campaign filename not needed for calibration
    return templates.mod_dynamic_parameters(config_builder, table)


def map_sample_to_model_input(sample_dict, template_set_name, scenario_name, campaign_filename, random_run_number=True):
    """
    This method is used directly by the scenario-running script. Do not change its name or argument list.
    s is a dict of user parameters that need mapping to actual model parameters
    """

    table = base_table_for_scenario(template_set_name=template_set_name, scenario_name=scenario_name,
                                    campaign_filename=campaign_filename)
    if random_run_number:
        table['Run_Number'] = random.randint(0, 65535)  # Random random number seed

    sample = copy.deepcopy(sample_dict)

    if 'BaseInfectivity' in sample:
        value = sample.pop('BaseInfectivity')
        table['Base_Infectivity'] = value

    if ('PreARTLinkMin' in sample) and ('PreARTLinkMax' in sample):
        min_value = sample.pop('PreARTLinkMin')
        max_value = sample.pop('PreARTLinkMax')
        if max_value > min_value:
            table['Actual_IndividualIntervention_Config__KP_PreART_Link.Ramp_Min'] = min_value
            table['Actual_IndividualIntervention_Config__KP_PreART_Link.Ramp_Max'] = max_value
        else:
            table['Actual_IndividualIntervention_Config__KP_PreART_Link.Ramp_Min'] = max_value
            table['Actual_IndividualIntervention_Config__KP_PreART_Link.Ramp_Max'] = min_value

    if ('MaleToFemaleYoung' in sample) and ('MaleToFemaleOld' in sample):
        young = sample.pop('MaleToFemaleYoung')
        old = sample.pop('MaleToFemaleOld')
        table['Male_To_Female_Relative_Infectivity_Multipliers'] = [young, young, old]

    risk_reduction_fraction = sample.pop('Risk Reduction Fraction') if 'Risk Reduction Fraction' in sample else float(
        'NaN')
    risk_ramp_rate = sample.pop('Risk Ramp Rate') if 'Risk Ramp Rate' in sample else float('NaN')
    risk_ramp_midyear = sample.pop('Risk Ramp MidYear') if 'Risk Ramp MidYear' in sample else float('NaN')

    for province in ['Homa_Bay', 'Kisii', 'Kisumu', 'Migori', 'Nyamira', 'Siaya']:
        key = '%sLOWRisk' % province
        if key in sample:
            value = sample.pop(key)
            param = 'Initial_Distribution__KP_Risk_%s' % province
            table[param] = [value, 1 - value, 0]

        if not math.isnan(risk_reduction_fraction):
            param = 'Actual_IndividualIntervention_Config__KP_Medium_Risk_%s.Ramp_Max' % province
            table[param] = risk_reduction_fraction

        if not math.isnan(risk_ramp_rate):
            param = 'Actual_IndividualIntervention_Config__KP_Medium_Risk_%s.Ramp_Rate' % province
            table[param] = risk_ramp_rate

        if not math.isnan(risk_ramp_midyear):
            param = 'Actual_IndividualIntervention_Config__KP_Medium_Risk_%s.Ramp_MidYear' % province
            table[param] = risk_ramp_midyear

    if 'RiskAssortivity' in sample:
        v = sample.pop('RiskAssortivity')
        table['Weighting_Matrix_RowMale_ColumnFemale__KP_RiskAssortivity'] = [
            [v, 1 - v, 0],
            [1 - v, v, v],
            [0, v, 1 - v]]

    for p in params:
        # print('Mapping parameter: %s' % p)
        if 'MapTo' in p:
            try:
                value = sample.pop(p['Name'])
            except KeyError:
                continue  # no mapping needed, key not present in sample

            if isinstance(p['MapTo'], list):
                for mapto in p['MapTo']:
                    table[mapto] = value
            else:
                table[p['MapTo']] = value

    # verify all parameters were mapped
    for name, value in sample.items():
        print('UNUSED PARAMETER:', name)
    assert(len(sample) == 0)  # All params used
    return table


# Compute hypersphere radius as a function of the number of dynamic parameters
volume_fraction = 0.1  # fraction of N-sphere area to unit cube area for numerical derivative
num_params = len([p for p in params if p['Dynamic']])

r = OptimTool.get_r(num_params, volume_fraction)
# Check, here's the formula for the volume of a N-sphere
computed_volume_fraction = math.exp(
    num_params / 2. * math.log(math.pi) - gammaln(num_params / 2. + 1) + num_params * math.log(r))

optimtool = OptimTool(
    params,
    constrain_sample,  # <-- Will not be saved in iteration state
    mu_r=r,  # <-- Mean percent of parameter range for numerical derivative.  CAREFUL with integer parameters!
    sigma_r=r / 10.,  # <-- stddev of above
    samples_per_iteration=N_SAMPLES_PER_ITERATION,
    center_repeats=10,  # 10 is real size, 2 is testing
    rsquared_thresh=0.81
    # Linear regression goodness of fit threshold, [0:1].  Above this, regression is used.  Below, use best point. Best to be fairly high.
)

calib_manager = CalibManager(
    name='%s--%s--rep%s--test%s' % (site_info['site_name'], BASE_POPULATION_SCALE_FACTOR, N_REPLICATES, TEST_N),
    config_builder=config_builder,
    map_sample_to_model_input_fn=map_sample_to_model_input_fn,
    sites=[site],
    next_point=optimtool,
    sim_runs_per_param_set=N_REPLICATES,
    max_iterations=N_ITERATIONS,
    plotters=plotters

)

# *******************************************************************
# Resampling specific code

# Define the resamplers to run (one or more) in list order.
resample_steps = [
    # can pass kwargs directly to the underlying resampling routines if needed
    RandomPerturbationResampler(M=1800, N=10, n=1),
    CramerRaoResampler(num_of_pts=1000)
]
# *******************************************************************

# REQUIRED variable name: run_calib_args . Required key: 'resamplers', even if empty.
run_calib_args = {
    'resamplers': resample_steps,
    'calib_manager': calib_manager,
    'scenario_template_sets': scenario_template_sets,  # This entry is required by run_scenarios.py
    'reference_info': reference_info  # This entry is required by run_scenarios.py
}

if __name__ == "__main__":
    SetupParser.init()
    calib_manager.run_calibration()
