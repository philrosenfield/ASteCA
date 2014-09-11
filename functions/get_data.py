"""
@author: gabriel
"""

import numpy as np
from os.path import join


def rem_bad_stars(id_star, x_data, y_data, mag_data, e_mag, col1_data,
        e_col1):
    '''
    Remove stars from all lists that have too large magnitude or color
    values (or their errors) which indicates a bad photometry.
    '''
    # Set value of maximum limit.
    min_lim, max_lim = -50., 50.

    # Store indexes of stars that should be removed.
    lists_arr = zip(mag_data, e_mag, col1_data, e_col1)
    del_indexes = [i for i, t in enumerate(lists_arr) if
        any(e > max_lim for e in t) or any(e < min_lim for e in t)]

    # Remove stars from id list first since this are strings.
    id_clean = np.delete(np.array(id_star), del_indexes)
    # Remove stars from the rest of the lists simultaneously.
    clean_array = np.delete(np.array([x_data, y_data, mag_data, e_mag,
        col1_data, e_col1]), del_indexes, axis=1)

    return id_clean, clean_array


def get_data(mypath, sub_dir, myfile, gd_params):
    '''
    Get photometric data from the cluster's data file.
    '''
    data_file = join(mypath, sub_dir, myfile)

    # Read indexes from input params.
    id_inx, x_inx, y_inx, m_inx, em_inx, c_inx, ec_inx = gd_params[:-1]

    # Loads the data in 'myfile' as a list of N lists where N is the number of
    # columns. Each of the N lists contains all the data for the column.
    # If any string is found (for example 'INDEF') it is converted to 99.999.
    data = np.genfromtxt(data_file, dtype=float, filling_values=99.999,
                         unpack=True)

    # Read data colums, except IDs.
    x_data, y_data, mag_data, e_mag, col1_data, e_col1 = \
    data[x_inx], data[y_inx], data[m_inx], data[em_inx],\
    data[c_inx], data[ec_inx]

    # Now read IDs as strings.
    data = np.genfromtxt(data_file, dtype=str, unpack=True)
    id_star = data[id_inx]
    n_old = len(id_star)

    # If any mag or color value (or their errors) is too large, discard
    # that star.
    id_star, [x_data, y_data, mag_data, e_mag, col1_data, e_col1] = \
    rem_bad_stars(id_star, x_data, y_data, mag_data, e_mag, col1_data, e_col1)

    print 'Data obtained from input file (N_stars: %d).' % len(id_star)
    if (n_old - len(id_star)) > 0:
        print ' Entries rejected: %d.' % (n_old - len(id_star))

    return id_star, x_data, y_data, mag_data, e_mag, col1_data, e_col1