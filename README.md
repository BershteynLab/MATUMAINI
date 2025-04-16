# MATUMAINI - Modeling the co-morbidity of HIV and CMD

* How does behavioral health impact HIV and HIV treatment outcomes?
* Common Mental Disorders (CMD) - depression and anxiety
    * can disrupt management of HIV - reducing engagement with care, testing, adherence, retention
    * can lead to risky behaviors which increase exposure risk
* HIV
    * positive diagnosis can increase risk of CMD through feelings of hopelessness, isolation, stigmatization, shame
    * successful treatment of HIV can reduce risk of CMD 
* How do the interactions between HIV and CMD contribute to the health burdens of both conditions?
    * Person-years spent depressed
    * HIV acquisitions
    * HIV-related mortality
    * Impact of ART, given reduced efficacy of ART among people with depression

## Project Outline

* [x] Implement CMD dynamical model within EMOD
    * [x] Add CMD Individual Property (IP) to EMOD which tracks individual CMD status
        * [x] Add CMD IP to the Demography File: `CMDStatus`
        * [x] Add CMD IP to the config file - report on IP
        * [x] Check: run calibrated model
        * [x] Revisit demographics and aging and how it interacts with recovery, relapse, and treatment history
            * [x] New mathematical model allows for already-depressed individuals to enter the next age bracket with memory of depression history
            * [x] Check: run calibrated model
    * [x] Integrate CMD into model with calibration - Proof of concept
        * [x] Implement simple SIS model of Depression
        * [x] Try calibrating with proof of concept
            * [x] Add CMD IP to dtk_post_process
            * [x] Add CMD prevalence calibration target to the ingest form
            * [x] Add CMD as a variable to be calibrated
    * [x] Develop R analysis tools for postprocessing
    * [x] Develop more detailed CMD model
        * [x] Add age and gender-related incidence modifiers
        * [x] Add different relapse rates for Treated and Untreated individuals
        * [x] Add differentiation between treatment and non-treatment
        * [x] Track individual treatment history, such that individuals who have received treatment are more likely to seek treatment again, less likely to have relapse
* [x] Implement interactions from CMD to HIV
    * [x] Increased risky behavior among those depressed
        * [x] Transition depressed individuals to MEDIUM risk
        * [x] Transition depressed individuals back when they recover, at appropriate rates 
    * [x] Delays to testing - interrupt HCT Testing Loop
        * [x] Add a check on HCTTestingLoop1 - HCTTestingLoopRapidTest
    * [x] ART adherence - differential dropout rates
    * [x] ART VLS outcomes
        * [x] Added effective/noneffective ART choice based on CMD status
        * [x] Added ARTMortality table
        * [x] Added transition from noneffective to effective ART following CMD recovery
    * [ ] Delays to initiating ART
* [x] Implement interactions from HIV to CMD
    * [x] Elevated depression incidence among HIV positive - CoitalActRiskFactors
    * [x] Adjust Risk Group to MEDIUM for depressed individuals
    * [x] Higher depression upon receiving diagnosis
    * [x] Increase depression recovery rate upon reaching VLS
    * [x] Linkage to treatment upon receiving depression diagnosis
* [ ] Future work: other preventative measures
    * [ ] PrEP
    * [ ] Condom use
    * [ ] VMMC
    * [ ] Next generation of depression treatment implementation
    * [ ] Add CMD-related excess mortality

## Major Updates

* 2025-04-16 - Saved repository to accompany manuscript submission
* 2024-09-07 - Generated results for first manuscript on `croi` branch
* 2024-03-03 - Presented results from `croi` branch at CROI 2024
* 2023-10-31 - Presented results from `nimh` branch at Global Mental Health Research without Borders Conference
    * Need to revisit treatment and diagnosis scenarios: 
        * link to depression care -> screening -> diagnosis -> treatment response
        * floated the possibility of implementing depression treatment distribution in the same way as PrEP distribution