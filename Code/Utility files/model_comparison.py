import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold, KFold
import seaborn as sns
import matplotlib.patches as mpatches
from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.stats import shapiro    
import matplotlib.pyplot as plt
import statsmodels.api as sm
import scipy
from scipy.stats import spearmanr
from sklearn.linear_model import RANSACRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.metrics import mean_squared_error, r2_score
import statsmodels.api as sm



class CrossValidation:
    def __init__(self, dfs, predictors, outcome, n_splits=10):
        self.dfs = dfs
        self.predictors = predictors
        self.outcome = outcome
        self.n_splits = n_splits
        self.gkf = GroupKFold(n_splits=n_splits)
        self.results_values = {}
        self.summary_outputs = []
        self.residuals_dict = {}


    def fit(self):
        self.results_wls_dict = {}  # Initialize a dictionary to store the results_wls objects
        results_values = {}

        for i, df in enumerate(self.dfs, start=1):  # start=1 to make the index 1-based
            r2_full, max_coeff_predictor, max_coeff_value, aic, bic, results_wls = self.fit_wls(df, i)
            rmse_mean, r2_mean = self.cross_validation(df, i)

            # Store the metrics for the current DataFrame
            results_values[f'DataFrame {i}'] = (rmse_mean, r2_mean, r2_full, max_coeff_predictor, max_coeff_value, aic, bic)

            # Store the results_wls object for the current DataFrame
            self.results_wls_dict[i] = results_wls

        # Convert the dictionary to a DataFrame and display it
        results_table = pd.DataFrame(list(results_values.items()), columns=['DataFrame', 'Metrics'])
        results_table[['Mean RMSE (CV)', 'R2 (CV)', 'R2 (Full)', 'Max Coeff Predictor', 'Max Coeff Value', 'AIC', 'BIC']] = pd.DataFrame(results_table.Metrics.tolist(), index= results_table.index)
        results_table = results_table.drop(columns=['Metrics'])
        print(results_table)

    def fit_wls(self, df, i):
        X = sm.add_constant(df[self.predictors])  # Adding the intercept term
        y = df[self.outcome]
        model = sm.OLS(y, X)
        results = model.fit()

        # Calculate residuals for the entire DataFrame
        residuals = y - results.predict(X)

        # Estimate weights as the inverse of the squared residuals for the entire DataFrame
        weights = 1.0 / (residuals ** 2)

        # Fit a WLS model on the entire DataFrame using the estimated weights
        model_wls = sm.WLS(y, X, weights=weights)
        results_wls = model_wls.fit(cov_type='HC3')  # Using HC3 covariance type

        # Get the p-values and coefficients from the model
        p_values = results_wls.pvalues
        coefficients = results_wls.params

        # Filter for significant coefficients
        significant_coefficients = coefficients[p_values < 0.05]

        # Drop 'const' from significant_coefficients
        if 'const' in significant_coefficients:
            significant_coefficients = significant_coefficients.drop('const')

        # Get the predictor with the highest absolute coefficient
        max_coeff_predictor = significant_coefficients.abs().idxmax()
        max_coeff_value = significant_coefficients[max_coeff_predictor]

        # Calculate R2 for the entire DataFrame
        r2_full = results_wls.rsquared

        #Get the summary output
        summary = results_wls.summary()

        # Get AIC and BIC of the model
        aic = results_wls.aic
        bic = results_wls.bic

        return r2_full, max_coeff_predictor, max_coeff_value, aic, bic, results_wls
    
    def print_summaries(self):
        for df_number, results_wls in self.results_wls_dict.items():
            print(f"Summary for DataFrame {df_number}:")
            print(results_wls.summary())

    def cross_validation(self, df, i):
        X = sm.add_constant(df[self.predictors])  # Adding the intercept term
        y = df[self.outcome]
        model = sm.OLS(y, X)
        results = model.fit()

        # Calculate residuals for the entire DataFrame
        residuals = y - results.predict(X)

        # Estimate weights as the inverse of the squared residuals for the entire DataFrame
        weights = 1.0 / (residuals ** 2)

        rmse_scores = []  # Initialize the RMSE scores for each DataFrame
        r2_scores = []  # Initialize the R2 scores for each DataFrame

        for fold, (train_index, test_index) in enumerate(self.gkf.split(df[self.predictors], df[self.outcome], df['PCS_ESE']), start=1): #inner loop performs loops over all kfolds, fits the model, and calculates RMSE
            # Split the data into training and test sets
            train, test = df.iloc[train_index], df.iloc[test_index]

            # Fit a WLS model on the training set using the corresponding weights
            X_train = X.iloc[train_index]
            y_train = y.iloc[train_index]
            weights_train = weights.iloc[train_index]
            model_wls = sm.WLS(y_train, X_train, weights=weights_train)
            results_wls = model_wls.fit()

            # Evaluate the model on the test set
            X_test = X.iloc[test_index]
            y_test = y.iloc[test_index]
            predictions = results_wls.predict(X_test)
            mse = mean_squared_error(y_test, predictions)
            rmse = np.sqrt(mse)  # Calculate RMSE
            rmse_scores.append(rmse)
            r2_scores.append(results_wls.rsquared)

        # Calculate the mean RMSE and R2 scores for the current DataFrame
        rmse_mean = np.mean(rmse_scores)
        r2_mean = np.mean(r2_scores)

        return rmse_mean, r2_mean
    

    
    def assess_normality(self):
        for i, df in enumerate(self.dfs, start=1):  # start=1 to make the index 1-based
            # Fit a WLS model on the entire DataFrame
            X = sm.add_constant(df[self.predictors])  # Adding the intercept term
            y = df[self.outcome]
            model = sm.OLS(y, X)
            results = model.fit()

            # Calculate residuals
            residuals = y - results.predict(X)

            # Plot a Q-Q plot of the residuals
            sm.qqplot(residuals, line='s')
            plt.title(f'Q-Q Plot of Residuals for DataFrame {i}')
            plt.show()

            # Perform a Shapiro-Wilk test on the residuals
            shapiro_test = shapiro(residuals)
            print(f'Shapiro-Wilk Test for DataFrame {i}: W={shapiro_test[0]}, p={shapiro_test[1]}')
    



    def plot_fitted_vs_raw_data(self):
        num_dfs = len(self.dfs)
        num_cols = 3
        num_rows = math.ceil(num_dfs / num_cols)

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(10 * num_cols, 6 * num_rows))
        axes = axes.flatten()
        for ax in axes[num_dfs:]:
            fig.delaxes(ax)

        for ax, df in zip(axes, self.dfs):
            df = df.copy()
            df['color'] = df['PCS_ESE'].str[0].astype(str)  # Ungrouped data
            grouped_df = df.groupby('PCS_ESE')[self.predictors + [self.outcome]].mean()  # Grouped data
            grouped_df['color'] = grouped_df.index.str[0].astype(str)

            # Fit a WLS model on the entire DataFrame
            X = sm.add_constant(grouped_df[self.predictors])  # Adding the intercept term
            y = grouped_df[self.outcome]
            model = sm.OLS(y, X)
            results = model.fit()

            # Calculate residuals
            residuals = y - results.predict(X)

            # Estimate weights as the inverse of the squared residuals
            weights = 1.0 / (residuals ** 2)

            # Fit a WLS model using the estimated weights
            model_wls = sm.WLS(y, X, weights=weights)
            results_wls = model_wls.fit()

            # Get the predicted values
            y_pred = results_wls.predict(X)

            # Plot raw data
            for color in df['color'].unique():
                ax.scatter(df.loc[df['color'] == color, self.predictors[0]], 
                           df.loc[df['color'] == color, self.outcome], 
                           label=f'PCS_ESE Class {color}')

            # Plot fitted line
            ax.plot(grouped_df[self.predictors[0]], y_pred, color='red', label='Fitted line')
            ax.set_title(f'Fitted vs Raw Data')
            ax.set_xlabel('Predictors')
            ax.set_ylabel(self.outcome)
            ax.legend()

        plt.tight_layout()
        plt.show()

    def plot_residuals(self):
        num_dfs = len(self.residuals_dict)
        num_cols = 3
        num_rows = math.ceil(num_dfs / num_cols)

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(10 * num_cols, 6 * num_rows))
        axes = axes.flatten()
        for ax in axes[num_dfs:]:
            fig.delaxes(ax)

        for ax, (df_fold, residuals) in zip(axes, self.residuals_dict.items()):
            sns.histplot(residuals, kde=True, ax=ax)
            ax.set_title(f'Residuals Distribution for {df_fold}')
            ax.set_xlabel('Residuals')
            ax.set_ylabel('Frequency')

        plt.tight_layout()
        plt.show()
    
    from scipy.stats import spearmanr

    def calculate_correlations_median(self, grouping_column):
        correlations = {}
        for i, df in enumerate(self.dfs, start=1):
            # Select only required columns
            df = df[self.predictors + [self.outcome, grouping_column]]
            # Group by grouping_column and calculate median coordinates
            df_grouped = df.groupby(grouping_column).median()

            if len(self.predictors) == 1:
                # If there's only one predictor, calculate the correlation and p-value directly
                corr_value, p_value = spearmanr(df_grouped[self.predictors[0]], df_grouped[self.outcome])
                corr_values = pd.Series([corr_value], index=self.predictors)
                p_values = pd.Series([p_value], index=self.predictors)
            else:
                # Calculate correlation with outcome for each predictor
                corr_values, p_values = spearmanr(df_grouped)
                corr_values = pd.Series(corr_values[-1, :-1], index=self.predictors)
                p_values = pd.Series(p_values[-1, :-1], index=self.predictors)

            # Get predictor with highest absolute correlation
            max_corr_predictor = corr_values.abs().idxmax()
            max_corr_value = corr_values[max_corr_predictor]
            max_p_value = p_values[max_corr_predictor]
            correlations[f'DataFrame {i}'] = (max_corr_predictor, max_corr_value, max_p_value)

        correlations_df = pd.DataFrame(list(correlations.items()), columns=['DataFrame', 'Max Correlation'])
        correlations_df[['Predictor', 'Correlation', 'P-value']] = pd.DataFrame(correlations_df['Max Correlation'].tolist(), index=correlations_df.index)
        correlations_df = correlations_df.drop(columns=['Max Correlation'])
        print(correlations_df)


    def plot_mean_true_vs_predicted(self):
        # Determine the layout of the subplots
        num_dfs = len(self.predictions_dict)
        num_cols = 3  # Change this to 3 for a 3x3 grid
        num_rows = math.ceil(num_dfs / num_cols)

        # Initialize a dictionary to store the mean predictions and true values for each PCS_ESE group
        mean_values_dict = {}

        # Calculate the mean predicted and true values for each PCS_ESE group
        for df_name, values in self.predictions_dict.items():
            mean_values_dict[df_name] = {}
            for y_test, predictions, pcs_ese in values:  # Expect three values here
                for pcs_ese_value in pcs_ese.unique():
                    mask = pcs_ese == pcs_ese_value
                    mean_values_dict[df_name][pcs_ese_value] = (predictions[mask].mean(), y_test[mask].mean())

        # Get all unique PCS_ESE values from all dataframes
        all_pcs_ese_values = set()
        for _, values in self.predictions_dict.items():
            for y_test, predictions, pcs_ese in values:
                all_pcs_ese_values.update(pcs_ese.unique())

        # Sort the PCS_ESE values
        all_pcs_ese_values = sorted(all_pcs_ese_values)

        # Create a color palette
        color_palette = sns.color_palette('hsv', len(all_pcs_ese_values))

        # Map each PCS_ESE group to a color
        color_map = {pcs_ese_value: color for pcs_ese_value, color in zip(all_pcs_ese_values, color_palette)}

        # Create a figure and a grid of subplots
        fig, axes = plt.subplots(num_rows, num_cols, figsize=(10 * num_cols, 6 * num_rows))

        # Flatten the axes array and remove extra subplots
        axes = axes.flatten()
        for ax in axes[num_dfs:]:
            fig.delaxes(ax)

        # Plot the mean true vs mean predicted values for each PCS_ESE group
        for ax, (df_name, pcs_ese_values) in zip(axes, mean_values_dict.items()):
            for pcs_ese_value, (mean_prediction, mean_true_value) in pcs_ese_values.items():
                color = color_map.get(pcs_ese_value, 'black')  # Use black as the default color
                sns.scatterplot(x=[mean_true_value], y=[mean_prediction], ax=ax, color=color)
            ax.set_title(f'Mean True vs Mean Predicted Values for {df_name}')
            ax.set_xlabel('Mean True Values')
            ax.set_ylabel('Mean Predicted Values')

        # Display the figure
        plt.tight_layout()
        plt.show()

        # Create a new figure for the legend
        fig_legend = plt.figure(figsize=(10, 2))  # Adjust the figure size as needed

        # Add the legend to the new figure
        legend_patches = [mpatches.Patch(color=color, label=pcs_ese_value) for pcs_ese_value, color in color_map.items()]
        plt.legend(handles=legend_patches, title='PCS_ESE', loc='center', ncol=3)  # Adjust the number of columns as needed
        plt.axis('off')

        # Display the legend
        plt.show()
    
    def plot_residuals_vs_fitted(self):
        num_dfs = len(self.predictions_dict)
        num_cols = 3
        num_rows = math.ceil(num_dfs / num_cols)

        residuals_dict = {}
        fitted_dict = {}

        for df_name, values in self.predictions_dict.items():
            residuals_dict[df_name] = {}
            fitted_dict[df_name] = {}
            for y_test, predictions, pcs_ese in values:
                for pcs_ese_value in pcs_ese.unique():
                    mask = pcs_ese == pcs_ese_value
                    residuals = y_test[mask] - predictions[mask]
                    # Standardize the residuals
                    residuals /= residuals.std()
                    residuals_dict[df_name][pcs_ese_value] = residuals
                    fitted_dict[df_name][pcs_ese_value] = predictions[mask]

        all_pcs_ese_values = set()
        for _, values in self.predictions_dict.items():
            for _, _, pcs_ese in values:
                all_pcs_ese_values.update(pcs_ese.unique())

        all_pcs_ese_values = sorted(all_pcs_ese_values)

        color_palette = sns.color_palette('hsv', len(all_pcs_ese_values))

        color_map = {pcs_ese_value: color for pcs_ese_value, color in zip(all_pcs_ese_values, color_palette)}

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(10 * num_cols, 6 * num_rows))

        axes = axes.flatten()
        for ax in axes[num_dfs:]:
            fig.delaxes(ax)

        for ax, (df_name, pcs_ese_values) in zip(axes, residuals_dict.items()):
            for pcs_ese_value, residuals in pcs_ese_values.items():
                color = color_map.get(pcs_ese_value, 'black')
                fitted_values = fitted_dict[df_name][pcs_ese_value]
                sns.scatterplot(x=fitted_values, y=residuals, ax=ax, color=color)
            ax.axhline(0, color='red', linestyle='--')  # Add a horizontal line at y=0
            ax.set_title(f'Standardized Residuals vs Fitted for {df_name}')
            ax.set_xlabel('Fitted values')
            ax.set_ylabel('Standardized Residuals')

        plt.tight_layout()
        plt.show()

        fig_legend = plt.figure(figsize=(10, 2))

        legend_patches = [mpatches.Patch(color=color, label=pcs_ese_value) for pcs_ese_value, color in color_map.items()]
        plt.legend(handles=legend_patches, title='PCS_ESE', loc='center', ncol=3)
        plt.axis('off')

        plt.show()
    
    def plot_grouped_residuals_vs_fitted(self):
        num_dfs = len(self.predictions_dict)
        num_cols = 3
        num_rows = math.ceil(num_dfs / num_cols)

        residuals_dict = {}
        fitted_dict = {}

        for df_name, values in self.predictions_dict.items():
            residuals_dict[df_name] = {}
            fitted_dict[df_name] = {}
            for y_test, predictions, pcs_ese in values:
                for pcs_ese_value in pcs_ese.unique():
                    mask = pcs_ese == pcs_ese_value
                    residuals = y_test[mask] - predictions[mask]
                    residuals_dict[df_name][pcs_ese_value] = residuals.mean()
                    fitted_dict[df_name][pcs_ese_value] = predictions[mask].mean()

        all_pcs_ese_values = set()
        for _, values in self.predictions_dict.items():
            for _, _, pcs_ese in values:
                all_pcs_ese_values.update(pcs_ese.unique())

        all_pcs_ese_values = sorted(all_pcs_ese_values)

        color_palette = sns.color_palette('hsv', len(all_pcs_ese_values))

        color_map = {pcs_ese_value: color for pcs_ese_value, color in zip(all_pcs_ese_values, color_palette)}

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(10 * num_cols, 6 * num_rows))

        axes = axes.flatten()
        for ax in axes[num_dfs:]:
            fig.delaxes(ax)

        for ax, (df_name, pcs_ese_values) in zip(axes, residuals_dict.items()):
            residuals_list = []
            fitted_values_list = []
            for pcs_ese_value, residuals in pcs_ese_values.items():
                color = color_map.get(pcs_ese_value, 'black')
                fitted_values = fitted_dict[df_name][pcs_ese_value]
                sns.scatterplot(x=[fitted_values], y=[residuals], ax=ax, color=color)
                residuals_list.append(residuals)
                fitted_values_list.append(fitted_values)

            # Calculate standard deviation of residuals
            residuals_std = np.std(residuals_list)

            # Define outlier threshold as 2.5 times the standard deviation
            outlier_threshold = 2.5 * residuals_std

            for pcs_ese_value, residuals in pcs_ese_values.items():
                fitted_values = fitted_dict[df_name][pcs_ese_value]

                # If the residuals are an outlier, add a label
                if abs(residuals) > outlier_threshold:
                    ax.text(fitted_values, residuals, pcs_ese_value, ha='center')

            # Calculate lowess line for all data
            lowess_line = lowess(residuals_list, fitted_values_list)

            # Calculate upper and lower bounds for smoothed area
            upper_bound = lowess_line[:, 1] + residuals_std
            lower_bound = lowess_line[:, 1] - residuals_std

            # Add smoothed area to plot
            ax.fill_between(lowess_line[:, 0], lower_bound, upper_bound, color='black', alpha=0.2)

            ax.axhline(0, color='red', linestyle='--')  # Add a horizontal line at y=0
            ax.set_title(f'Mean Residuals vs Mean Fitted for {df_name}')
            ax.set_xlabel('Mean Fitted values')
            ax.set_ylabel('Mean Residuals')

        plt.tight_layout()
        plt.show()

        fig_legend = plt.figure(figsize=(10, 2))

        legend_patches = [mpatches.Patch(color=color, label=pcs_ese_value) for pcs_ese_value, color in color_map.items()]
        plt.legend(handles=legend_patches, title='PCS_ESE', loc='center', ncol=3)
        plt.axis('off')

        plt.show()
    
   
   