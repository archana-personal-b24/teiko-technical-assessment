PRAGMA foreign_keys = ON;
CREATE TABLE subjects (subject_id TEXT PRIMARY KEY, project TEXT NOT NULL, condition TEXT NOT NULL, age INTEGER NOT NULL CHECK(age>=0), sex TEXT NOT NULL CHECK(sex IN ('M','F')), treatment TEXT NOT NULL, response TEXT CHECK(response IN ('yes','no') OR response IS NULL));
CREATE TABLE samples (sample_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES subjects(subject_id), sample_type TEXT NOT NULL, time_from_treatment_start INTEGER NOT NULL);
CREATE TABLE cell_counts (sample_id TEXT NOT NULL REFERENCES samples(sample_id) ON DELETE CASCADE, population TEXT NOT NULL CHECK(population IN ('b_cell','cd8_t_cell','cd4_t_cell','nk_cell','monocyte')), count INTEGER NOT NULL CHECK(count>=0), PRIMARY KEY(sample_id,population));
CREATE INDEX idx_subject_cohort ON subjects(condition,treatment,response,sex);
CREATE INDEX idx_sample_subset ON samples(sample_type,time_from_treatment_start);
CREATE VIEW sample_frequencies AS WITH totals AS (SELECT sample_id,SUM(count) total_count FROM cell_counts GROUP BY sample_id) SELECT c.sample_id sample,t.total_count,c.population,c.count,100.0*c.count/NULLIF(t.total_count,0) percentage FROM cell_counts c JOIN totals t USING(sample_id);
CREATE TABLE analysis_results (population TEXT PRIMARY KEY,n_responders INTEGER NOT NULL,n_nonresponders INTEGER NOT NULL,mean_responder REAL NOT NULL,mean_nonresponder REAL NOT NULL,mean_difference REAL NOT NULL,t_statistic REAL NOT NULL,p_value REAL NOT NULL,adjusted_p_value REAL NOT NULL,cohens_d REAL NOT NULL,significant INTEGER NOT NULL CHECK(significant IN (0,1)));
