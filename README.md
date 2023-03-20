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
    * [ ] Integrate CMD into model with calibration
        * [x] Add CMD IP to dtk_post_process
        * [x] Add CMD prevalence calibration target to the ingest form
        * [ ] Add CMD transitions based on age-dependent incidence, remission (assume no treatment for now)
        * [ ] Add ARTMortality Table - differentiating efficacy of care
        * [ ] Alter Ingest form to include age-dependent incidence as a free parameter to calibrate to
        * [ ] Check: re-calibrate model, check that it still runs
    * [ ] Add CMD-related excess mortality
    * [ ] Add CMD transitions based on treatment
    * [ ] Run model to test
* [ ] Implement interactions between CMD and HIV
* [ ] Re-calibrate model with CMD