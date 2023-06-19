# MATUMAINI - Modeling the co-morbidity of HIV and CMD

* How does behavioral health impact HIV and HIV treatment outcomes?
* Common Mental Disorders (CMD) - depression and anxiety
    * can disrupt management of HIV - reducing engagement with care, testing, adherence, retention
    * can lead to risky behaviors which increase exposure risk
* HIV
    * positive diagnosis can increase risk of CMD through feelings of hopelessness, isolation, stigmatization, shame
    * successful treatment of HIV can reduce risk of CMD 

## Project Outline

* [ ] Implement [model of CMD](https://docs.google.com/presentation/d/1LaGunWwd2bJYsFmCAZPay9UfXygRY47RvCdVJKmSLjA/edit?usp=sharing) within EMOD
    * [x] Add CMD Individual Property (IP) to EMOD which tracks individual CMD status
        * [x] Add CMD IP to the Demography File: `CMDStatus`
        * [x] Add CMD IP to the config file - report on IP
        * [x] Check: run calibrated model
    * [x] Integrate CMD into model with calibration - Proof of concept
        * [x] Implement simple SIS model of Depression
        * [x] Try calibrating with proof of concept
            * [x] Add CMD IP to dtk_post_process
            * [x] Add CMD prevalence calibration target to the ingest form
            * [x] Add CMD as a variable to be calibrated
    * [x] Develop R analysis tools for postprocessing
    * [ ] Develop more detailed CMD model
        * [x] Add age and gender-related incidence modifiers
        * [ ] Add different relapse rates for Treated and Untreated individuals
        * [ ] Add CMD-related excess mortality
        * [ ] Add differentiation between treatment and non-treatment
        * [ ] Track individual treatment history, such that individuals who have received treatment are more likely to seek treatment again, less likely to have relapse
* [ ] Implement interactions between CMD and HIV
    * [x] Increased risky behavior among those depressed
        * [x] Transition depressed individuals to MEDIUM risk
        * [x] Transition depressed individuals back when they recover, at appropriate rates 
    * [x] ART VLS outcomes
        * [x] Added effective/noneffective ART choice based on CMD status
        * [x] Added ARTMortality table
        * [x] Added transition from noneffective to effective ART following CMD recovery
    * [x] Delays to testing - interrupt HCT Testing Loop
        * [x] Add a check on HCTTestingLoop1 - HCTTestingLoopRapidTest
    * [x] ART adherence - differential dropout rates
* [ ] Re-calibrate full model with CMD
* [ ] Future work: other preventative measures
    * [ ] PrEP
    * [ ] Condom use
    * [ ] VMMC
* [ ] Future work: Influence of HIV on depression
    * [ ] Higher depression upon receiving diagnosis
    * [ ] Reduced depression upon achieving VLS
    * [ ] Linkage to treatment upon receiving depression diagnosis