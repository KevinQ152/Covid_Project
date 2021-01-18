import pandas as pd
import numpy as np
from sklearn.datasets import make_regression
from sklearn.isotonic import IsotonicRegression
import random
import copy

# Note lmafit.py needs to be in the same directory for now
from lmafit import lmafit_mc_adp

# A class that performs some matrix operations and methods specifically on
# Pandas dataframes

class mat_opr:
    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.array = self.dataframe.values.tolist()


    def known(self, unknowns = None):
        # returns a list of tuples with indices for known entries in the matrix

        # unkowns can take the value 0 in order to represent zeros as unkowns

        indices = []
        for i in range(len(self.array)):
            for j in range(len(self.array[i])):
                if unknowns == 0:
                    if self.array[i][j] != 0:
                        indices.append((i,j))
                else:
                    if not(self.array[i][j] is None or self.array[i][j] is np.nan):
                        indices.append((i,j))

        return indices

    def drop_zero_rows(self, val=0):
        # drops any row that contains all zeros or all of the value provided in val
        newframe = self.dataframe.loc[(self.dataframe!=val).any(axis=1)]
        self.dataframe = newframe

    def drop_zero_cols(self, val=0):
        # drops any column that contains all zeros or all of the value provided in val
        newframe = self.dataframe.loc[:, (self.dataframe!=val).any(axis=0)]
        self.dataframe = newframe

    def hide_rows(self, percent):
        # returns a new mat_opr object with a specified percent of the original rows randomly hidden
        new_arr = self.dataframe.copy(deep=True)

        num_hide = int(len(new_arr.index)*percent)
        to_hide = random.sample(list(new_arr.index), num_hide)

        for t in to_hide:
            new_arr = new_arr.drop(t, axis=0)

        return mat_opr(new_arr)

    def hide_cols(self, percent):
        # returns a new mat_opr object with a specified percent of the original columns randomly hidden
        new_arr = self.dataframe.copy(deep=True)

        num_hide = int(len(new_arr.columns)*percent)
        to_hide = random.sample(list(new_arr.columns), num_hide)

        for t in to_hide:
            new_arr = new_arr.drop(t, axis=1)

        return mat_opr(new_arr)

    def hide_entries(self, percent, val = None):
        # Hides a percent of the known entries in the dataframe
        # returns a new hidden mat_opr object and a dictionary for indexes and values
        # of the entries that were hidden

        # val takes a value that "represents" a hidden value
        # ex) None or 0

        new_arr = self.dataframe.copy(deep=True)
        knowns = self.known(val)

        num_hide = int(len(knowns)*percent)
        to_hide = random.sample(knowns, num_hide)

        hiders = {}
        for t in to_hide:
            hiders[t] = new_arr.iloc[t[0],t[1]]
            new_arr.iloc[t[0],t[1]] = val

        return mat_opr(new_arr), hiders

    def is_row_inc(self, printy=True):
        # Tests if the data frame is row increasing
        # prints results if printy is set to True
        # returns a dictionary of indices where the dataframe is not increasing
        # dictionary structure: {row index: [column indices]}

        # DOES not include cases where the entry is 0 or unkown

        non_inc = {}
        for i in range(len(self.array)):
            last = self.array[i][0]
            spots = []
            for j in range(len(self.array[0])):
                if self.array[i][j] != 0 and not np.isnan(self.array[i][j]):
                    if self.array[i][j] < last:
                        spots.append(j)
                    last = self.array[i][j]

            if len(spots) != 0:
                non_inc[i] = spots

        if printy == True:
            print(str(len(non_inc)) + " rows are non increasing in at least one spot")
        return non_inc

    def is_col_inc(self, printy=True):
        # Tests if the data frame is column increasing
        # prints results if printy is set to True
        # returns a dictionary of indices where the dataframe is not increasing
        # dictionary structure: {column index: [row indices]}

        # DOES not include cases where the entry is 0 or unkown

        non_inc = {}
        for i in range(len(self.array[0])):
            last = self.array[0][i]
            spots = []
            for j in range(len(self.array)):
                if self.array[j][i] != 0 and not np.isnan(self.array[j][i]):
                    if self.array[j][i] < last:
                        spots.append(j)
                    last = self.array[j][i]

            if len(spots) != 0:
                non_inc[i] = spots

        if printy == True:
            print(str(len(non_inc)) + " columns are non increasing in at least one spot")
        return non_inc

    def iso(self, axis=1):
        # performs isotonic regression row-wise (axis = 0) or column-wise (axis = 1)
        tonic = copy.deepcopy(self.array) # returns a new isotonic matrix

        # dat dict tells me where things arent increasing (from is_row_inc() or is_col_inc())
        if axis == 1:
            dat_dict = self.is_col_inc(False)
            for i in dat_dict.keys():
                initial_vals = [tonic[j][i] for j in range(len(tonic))]
                X = list(range(len(initial_vals)))

                # Use the initial values to fit the model and then predict what the decreasing ones should be
                iso = IsotonicRegression().fit(X,initial_vals)
                predictions = iso.predict(range(len(tonic)))

                # put everything back:
                for row in range(len(predictions)):
                    tonic[row][i] = predictions[row]

        else:
            dat_dict = self.is_row_inc(False)

            for i in dat_dict.keys():
                initial_vals = list(tonic[i].copy())
                X = list(range(len(tonic[i])))

                # Use the initial values to fit the model and then predict what the decreasing ones should be
                iso = IsotonicRegression().fit(X,initial_vals)
                predictions = iso.predict(range(len(tonic[i])))

                # put everything back:
                tonic[i] = predictions

        newframe = pd.DataFrame(tonic)
        return mat_opr(newframe)

    def lmafitter(self, rank = None, val=0):
        # Perfroms low-rank matrix completion using the methods from lmafit.py
        # val takes the value of unknowns ex) either 0 or None
        # rank takes an approximate rank for the matrix
        if rank is None:
            rank = np.linalg.matrix_rank(self.array)

        #First need to make the arrays needed
        known_seq = [[],[]]
        known_values = []
        known_ind = self.known(val)
        for i in known_ind:
            known_seq[0].append(i[0])
            known_seq[1].append(i[1])
            known_values.append(self.array[i[0]][i[1]])

        # something here has been deprecated. Not sure how to fix yet.
        known_indices = [tuple(known_seq[0]), tuple(known_seq[1])]
        known_values = [tuple(known_values)]




        X,Y,out = lmafit_mc_adp(len(self.array),len(self.array[0]),rank,known_indices,known_values)

        return X,Y,out
