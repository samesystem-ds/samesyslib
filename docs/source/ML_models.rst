Machine learning models in SameSystem
*************************************

ML models currently in use:

-  Daily model
-  Hourly model

Old versions
============

Daily model
-----------

Example of “old algo” replication, making forecast for 2019 August, :

calculating average day of week contribution on that month:

.. code:: python

   dow = s9422[s9422.year.isin([2018, 2017]) & s9422.month.isin([8])]\
           .groupby('dayofweek').agg({'amount':'mean'})

Calculating average week of month contribution for the same period as
above:

.. code:: python

   wom = s9422[s9422.year.isin([2018, 2017]) & s9422.month.isin([8])]\
           .groupby('week_of_month').agg({'amount':'mean'})

Making forecast (shares on that month):

.. code:: python

   f9422 = s9422[s9422.year.isin([2019]) & s9422.month.isin([8])]\
       [['dayofmonth','month','dayofweek', 'week_of_month', 'amount']].copy()
   for index, row in f9422.iterrows():
       f9422.loc[index, 'forecast'] = wom.loc[row['week_of_month']].amount \
                                       * dow.loc[row['dayofweek']].amount

   # Normalizing forecast
   f9422['forecast'] = f9422['forecast']/f9422['forecast'].sum()

The forecast in the system is displayed as last years total sales on
that month, multiplied by predicted shares:

.. code:: python

   f9422['forecast'] = s9422[s9422.year.isin([2018])\
                            & s9422.month.isin([8])].amount.sum() * f9422['forecast']

Hourly model
------------

Currently we don’t have good documentation how this model works. If you
like to understand it from the code, probably good starting point is
`here <https://github.com/samesystem/samesystem/blob/c7087be8c9d026911ac3de00693ea90028a3179a/app/models/schedule/shop_days/days_info.rb#L83>`__
But this seems to separate weekdays by months, and averages distribution
for each weekday. On top there seems to be some smoothing, but it is
hard to tell kind of it exactly.

Predicted hourly sales for a day are normalized to sum up to 1.

When predicting sales/foot traffic/number of transactions, predicted net
sales are multiplied by last years sales/foot traffic/number of
transactions and adjusted by predicted sales index. E.g., if this month
predicted sales are 20% higher, last years net sales/foot traffic/number
of transactions are increased by 20%.

New versions
============

.. _daily-model-1:

Daily model
-----------

Daily model by design makes predictions for one year ahead. For that,
the minimum data requirements are slightly above 1 year of historical
data. This “slightly” above means, that as yearly seasonality is
determined by moving average smoothing, we have undefined edges, which
has size of half window size ~30 days.

Our approach to daily model follows classical time series decomposition
(default: multiplicative), where times series y:

``y = T x S x R``

That is, prediction is composed of

Model initialization
~~~~~~~~~~~~~~~~~~~~

Input parameters to the daily model:

-  historical data
-  target [string] column name of target variable, must be in historical
   data provided
-  features [list] column names of the features for the model
-  test_fraction [float] fraction of historical data allocated for the
   test period. If there is enough historical data, the length of test
   period will be period_length*test_fraction, but limited to stay <=
   365 days.
-  best_features, best_model_weight_type, best_model_type are optional
   parameters used in dev phase to override internal optimization
   procedures

Minimum set of input parameters what must be supplied:
``m = hammer(shop_data, target=target, features = feature_list)`` also
check out notebook with minimal example
(daily_model/daily_initialization.ipynb).

At model initialization step we set, that we do not consider data older
then 2012-01-01. This parameter is hard-coded.

We perform automatic analysis to determine the most recent continuous
period on which we can perform model train, model should have at least
`minimum training length + test
period <https://github.com/samesystem-ds/Daily-Amount-Model/blob/9a2e8d5aaa782d93c9f7bfedc08a39ee0956e0f9/utilities.py#L271>`__.

After the code review, it was determined, that the minimum training
length is 365 days and minimum test period is 1 day. Putting all this
together we get 366 days as minimum date necessary for successful
modelling attempt.

Additionally, there is requirement for data continuity. If there is
break is data longer then 180 days, we break historical data into two
segments and perform fit only on the most recent data. See examples
(daily_model/daily_initialization_gap_logic.ipynb).

We support varying working days per week scenario’s, but model will fail
if there is only 1 working day per week.

Removal of outliers
~~~~~~~~~~~~~~~~~~~

For the outlier removal we are using inter-quartile range (IQR) based
`method <https://en.wikipedia.org/wiki/Interquartile_range#/media/File:Boxplot_vs_PDF.svg>`__,
where IQR is equal difference between 75th (q75) and 25th (q25)
quartiles. Then, outlier is defined as data point lying above
``q75 + 1.5*IQR`` or below ``q25 - 1.5*IQR``. This would be equivalent
to the removal of data points above or below 2.7 sigmas on normal
distribution. +/- 2.7 sigmas around the mean in normal distribution
covers 99.3% of data points, therefore if data is normal we should see
removal of 0.007% of data points
(daily_model/daily_model_outlier_logic.ipynb).

To make outliers detection robust even in cases with strong yearly
trends and monthly seasonality, IQR is derived on 180 days moving
window.

Days around state holidays and activities are not considered as
outliers, even if they show extreme variability.

Trend determination
~~~~~~~~~~~~~~~~~~~

.. _trend-determination-1:

Trend determination
~~~~~~~~~~~~~~~~~~~

For the trend determination it is important to well separate yearly
seasonality and trend which has longer frequency of variation. After
thorough testing, we found, that fbprophet forecasting tool does trend
determination job well enough.

Fbprophet simultaneously fits trend and seasonality, also allowing for
automatic detection of abrupt change-points, which are incorporated into
trend. Parameters used for fbprophet, while performing trend
determination:
``m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False, changepoint_prior_scale=0.05)``
note, that additive decomposition is used be default. During testing
with extreme multiplicative time series examples, this causing issues.

More details about some test cases see
daily_model/daily_model_trend.ipynb.

Estimation of monthly seasonalty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once trend is determined, we estimate monthly seasonality with a method
based on moving window averaging.

Depending on the type of decomposition, we perform additive or
multiplicative de-trending procedure: ``S = y/T`` or ``S = y - T``
respectively for multiplicative or additive decomposition. De-trended
time series are smoothed with a 31 days moving average window, 2 times.
Firstly with a 31 days moving window medians and then with a 31 days
arithmetic means. Lastly, third pass is performed with 3 days moving
average arithmetic mean. Moving average is centered (pandas option
center = True) and uses min_periods = 31//2 = 15. This guarantees that
we have valid values ant the ends of interval, especially when
historical data is minimal, e.g. 365 days.

Once we have smoothed seasonality data, we assign weights for each data
point. Weights are applied as a step function, which have constant
values for 365 days period.
``weight = ((date.max() - date).days // 365) ** memory_alpha`` The
functional form of the weights depends on the ‘memory_alpha’ parameter.
If memory_alpha = 0, then all days have identical weights. If
memory_alpha = 1, weight descends linearly from the most recent data to
the oldest, and if memory_alpha > 1, if descends as a power law. Simply
speaking, the larger memory alpha, the faster model forgets old data
when estimating seasonality.

If we have more then 2 years of historical data, we can perform
automatic optimization of memory_alpha. Automatic optimizer loops
through values in list [0,1,2,3]. The best according to average rmse
metric is selected. If there is less then 2 years of data, we select
memory_alpha = 2 as default value.

Once memory_alpha is set, we perform group by on seasonality time-series
on day of year variable and average according to weights value for each
day. To ensure we smoothly predict for leap years, in prediction model
we normalize day of year variable to be in range 0-1, and perform
interpolation for each predicted year with the day of year variable
similarly normalized.

At the end of this step we have both additively and multiplicatively
decomposed trend and seasonality component.

Testing on how model separates constant vs varying seasonality can be
found in the notebook daily_model/daily_model_seasonality.ipynb.

XGboost prediction
~~~~~~~~~~~~~~~~~~

Once we have trend and seasonality components ready, we perform last
step, train model on the residual time-series: de-trended and
de-seasonalized.

With each type of time series decomposition (multiplicative and
additive) we calculate 3 xgboost model types:

-  equal weights through-out historical data;
-  linearly decreasing weights from most recent to oldest data;
-  weight decreasing as power law, using same power index as monthly
   seasonality optimizer determined to be the optimal

Cross-validation procedure determines bet type of model to use and
number of iterations. Procedure for each model is as follows:

-  split time series according to TimeSeriesSplit `sklearn
   routine <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html>`__,
   progressively growing train period and constant size test period. We
   are using constant 5 folds on cross validation;
-  estimating rmse error metric on test period we also taking into
   account error from seasonality component by using predicted
   seasonality on evaluation;
-  multiplicative model in xgboost is treated as log variables,
   therefore final xgboost prediction is result of multiplication of all
   features;
-  error metrics are weighted according to train period size;
-  best model is selected according to rmse metric;
-  optimal number of iterations is selected by weighted (according to
   train period size) averaging of optimal number of iteration in cross
   validation. Number of iterations is capped on the lower end to be
   200.

Details on additive and multiplicative model automatic selection could
be found in the notebook daily_model/daily_model_xgboost.ipynb.

Feature’s
^^^^^^^^^

Trend and seasonality modules uses historical data as a whole for
predictions. And should cover low frequency signals in the data, ranging
from inter-year into monthly.

Xgboost tain model on the residual time series, and is working with a
data of higher frequency, that is with a frequencies below 30 days.

For those frequencies we are using features:

-  day of week [0-6]
-  month [1-12]
-  year [2020, 2021 …]
-  week of month grouped [10-128], where decimals correspond to months
   (1X - january, 2X - february) and digits to the week of month (X0 -
   first week, X8 - last week)
-  adjusted day of month/adjusted month is a feature which assigns same
   index for all similar day of weeks through-out historical data

Additionally we include: - state holidays feature is composed of
leading, over and trailing dummy variables. Leading part of state
holiday starts 5 days pbefore event and grows by values 16, 33, 50, 66
83. Over part of state holiday stays 100 over period of state holiday.
Trailing part of state holidays tarts at value 83 and decreases to 16 in
5 days period. All other days has value 0. - activities [0-1],
activities feature are created as dummy variables for each activity,
where start date of activity has value >0, which grows until end date
when it reaches value 1
