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
    * [ ] Add CMD Individual Property (IP) to EMOD which tracks individual CMD status
        * [x] Add CMD IP to the Demography File
        * [x] Add CMD IP to the config file - report on IP
        * [ ] Check: run calibrated model
    * [ ] Integrate CMD into model with calibration
        * [ ] Add CMD prevalence calibration target to the ingest form
        * [ ] Add CMD IP to dtk_post_process
        * [ ] Check: re-calibrate model, check that it still runs
    * [ ] Add CMD transitions based on age-dependent incidence, treatment, remission
    * [ ] Add CMD-related excess mortality
    * [ ] Run model to test
* [ ] Implement interactions between CMD and HIV
* [ ] Re-calibrate model with CMD