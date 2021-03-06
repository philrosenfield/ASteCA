# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 09:00:00 2014

@author: gabriel
"""

from update_check import updater
from os.path import join, isfile, isdir
import sys
import traceback
from subprocess import Popen, PIPE


def pack_check():
    '''
    Check if packages are installed.
    '''
    # Wrap in try statement to catch if 'pip' is not installed.
    try:
        import pip
        # check for globally installed packages.
        inst_packgs = pip.get_installed_distributions(local_only=False)
        inst_packgs_lst = ["%s" % (i.key) for i in inst_packgs]
        missing_pckg = []
        for pckg in ['numpy', 'matplotlib', 'scipy', 'astroml',
                     'scikit-learn']:
            if pckg not in inst_packgs_lst:
                missing_pckg.append(pckg)

        if missing_pckg:
            print "ERROR: the following packages are missing:\n"
            for p in missing_pckg:
                print " - {}".format(p)
            sys.exit("\nInstall with: pip install <package>\n")
    except ImportError:
        # Python versions 2.7.7 onward apparently have 'pip' included by
        # default, so this check should become obsolete.
        print("  WARNING: 'pip' is not present. Can't check for installed"
              " packages.\n")
        # Return empty list.
        inst_packgs_lst = []

    return inst_packgs_lst


def R_inst_packages():
    '''
    Check installed packages inside R.
    '''
    from rpy2.rinterface import RRuntimeError
    from rpy2.robjects.packages import importr
    utils = importr('utils')
    try:
        pack_lst = utils.installed_packages()
        rpack = list(pack_lst.rx(True, 1))
    except RRuntimeError:
        rpack = []
    return rpack


def R_check(inst_packgs_lst):
    '''
    Check if R and rpy2 are installed.
    '''
    rpy2_inst, R_inst = True, True
    # Check if rpy2 package is installed.
    if 'rpy2' not in inst_packgs_lst:
        rpy2_inst = False
    # Now check for R.
    proc = Popen(["which", "R"], stdout=PIPE, stderr=PIPE)
    exit_code = proc.wait()
    if exit_code != 0:
        R_inst = False

    R_in_place = False
    # If both R and rpy2 packages are installed.
    if R_inst and rpy2_inst:
        # Check if all needed packages within R are installed.
        needed_packg = ['ks', 'rgl']
        rpack = R_inst_packages()
        missing_pckg = []
        for pck in needed_packg:
            if pck not in rpack:
                missing_pckg.append(pck)

        if not missing_pckg:
            # R, rpy2 and all packages are installed, function is good to go.
            R_in_place = True
        else:
            # A package is missing in R.
            print ("  WARNING: the following packages are missing in R:\n")
            for p in missing_pckg:
                print " - {}".format(p)
            print ("\n  The 'KDE p-value test' function will be skipped.\n")
    else:
        if R_inst and not rpy2_inst:
            R_pack = "'rpy2' is"
        if rpy2_inst and not R_inst:
            R_pack = "'R' is"
        if not R_inst and not rpy2_inst:
            R_pack = "'R' and 'rpy2' are"
        # Something is not installed and function was told to run.
        print ("  WARNING: {} not installed and the 'KDE p-value test'\n"
               "  was set to run. The function will be skipped.\n".format(
                    R_pack))

    return R_in_place


def find_missing(arr_large, arr_small):
    '''
    Takes two arrays of floats, compares them and returns the missing
    elements in the smaller one.
    '''
    # Convert to strings before comparing.
    s1 = [str(_) for _ in arr_small]
    s2 = [str(_) for _ in arr_large]
    # Find missing elements. Convert to float and store.
    missing = [float(_) for _ in s2 if _ not in set(s1)]

    return missing


def check(mypath, file_end, cl_files):
    '''
    Checks that the necessary files are in place, that the parameters stored
    in the input file are valid and that the ranges given for the cluster
    parameters are consistent with the isochrones available before moving
    on with the code.
    '''

    print('Checking input parameters...\n')

    # Check that all packages are installed.
    inst_packgs_lst = pack_check()
    # If all packages are installed, load them up.
    import numpy as np

    # Custom functions.
    import _in.get_in_params as g
    from _in.get_names_paths import names_paths as n_p
    import _in.get_isoch_params as isochp
    from _in.get_met_ages_values import get_m_a_vls

    # Check that at least one photometric cluster file exists.
    if not cl_files:
        sys.exit("ERROR: no photometric data files found in '{}'\n"
                 "folder. Halting.".format('/input' + file_end))

    # Check if params_input_XX.dat file exists.
    pars_f_name = 'params_input' + file_end + '.dat'
    pars_f_path = join(mypath, pars_f_name)
    if file_end == '':
        if not isfile(pars_f_path):
            sys.exit("ERROR: '{}' file does not exist.".format(pars_f_name))
    else:
        if not isfile(pars_f_path):
            print ("  WARNING: {} file does not exist.\n  Falling back to"
                   " 'params_input.dat' file.\n".format(pars_f_name))

            # Fall back to default file.
            pars_f_name = 'params_input.dat'
            pars_f_path = join(mypath, pars_f_name)
            if not isfile(pars_f_path):
                sys.exit("ERROR: '{}' file does not exist.".format(
                    pars_f_name))

    # Check if params_input_XX.dat file is properly formatted.
    try:
        # Read input parameters from params_input.dat file. Initialize
        # global variables.
        g.init(mypath, pars_f_path)
    except Exception:
        # Halt code.
        print traceback.format_exc()
        sys.exit("ERROR: '{}' is badly formatted.".format(pars_f_name))

    # Check if a new version is available.
    if g.up_flag:
        updater()

    # Check mode.
    if g.mode not in {'auto', 'semi', 'manual'}:
        sys.exit("ERROR: 'mode' value selected ('{}') is not valid.".format(
            g.mode))

    if g.mode == 'semi':
        # Check if semi_input.dat file exists.
        semi_file = 'semi_input.dat'
        if not isfile(join(mypath, semi_file)):
            # File semi_input.dat does not exist.
            sys.exit("ERROR: 'semi' mode is set but semi_input.dat file does"
                     " not exist.")

    # Check px/deg.
    if g.gd_params[-1] not in {'px', 'deg'}:
        sys.exit("ERROR: the coordinate units given in the input parameters\n"
                 "file ('{}') are incorrect.".format(g.gd_params[-1]))

    # Selected CMD.
    if g.ps_params[1] not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}:
        sys.exit("ERROR: the stored CMD value ({}) does not match a valid"
                 " selection.".format(g.ps_params[1]))

    # Output figure.
    if g.pl_params[0] is True:
        if g.pl_params[1] not in {'png', 'pdf', 'PNG', 'PDF'}:
            sys.exit("ERROR: figure output format selected ('{}') is"
                     " not valid.".format(g.pl_params[1]))

    # 2D positional histogram.
    if g.gh_params[0] not in {'auto', 'manual'}:
        sys.exit("ERROR: mode selected ('{}') for 2D histogram"
                 " is not valid.".format(g.gh_params[0]))

    # Radius finding function.
    if g.cr_params[0] not in {'low', 'mid', 'high'}:
        sys.exit("ERROR: mode selected ('{}') for radius finding"
                 " function is not valid.".format(g.cr_params[0]))

    # Errors function.
    if g.er_params[0] not in {'emax', 'lowexp', 'eyefit'}:
        sys.exit("ERROR: mode selected ('{}') for error rejecting"
                 " function is not valid.".format(g.er_params[0]))
    if g.er_params[0] == 'emax' and len(g.er_params[1:]) < 1:
        sys.exit("ERROR: missing parameters for error rejecting function")
    if g.er_params[0] == 'eyefit' and len(g.er_params[1:]) < 3:
        sys.exit("ERROR: missing parameters for error rejecting function")
    if g.er_params[0] == 'lowexp' and len(g.er_params[1:]) < 4:
        sys.exit("ERROR: missing parameters for error rejecting function")

    # Check KDE p-value custer probability function.
    if g.pv_params[0] not in {'auto', 'manual', 'skip'}:
        sys.exit("ERROR: Wrong name ('{}') for 'mode' in KDE p-value test."
                 .format(g.pv_params[0]))
    elif g.pv_params[0] in {'auto', 'manual'}:
        # Check if R and rpy2 are installed.
        R_in_place = R_check(inst_packgs_lst)
    else:
        # Function was told not to run so we don't care if R and/or rpy2 are
        # installed since it will be skipped anyway.
        R_in_place = True

    # Check decont algorithm params.
    mode_da = g.da_params[0]
    # Check if 'mode' was correctly set.
    if mode_da not in ['auto', 'manual', 'read', 'skip']:
        sys.exit("ERROR: Wrong name ('{}') for decontamination algorithm "
                 "'mode'.".format(mode_da))

    if mode_da == 'read':
        # Check if file exists.
        for cl_file in cl_files:

            # Get memb file names.
            memb_file = n_p(cl_file)[2]
            if not isfile(memb_file):
                # File does not exist.
                sys.exit("ERROR: 'read' mode was set for decontamination "
                         "algorithm but the file:\n\n {}\n\ndoes not "
                         "exist.".format(memb_file))

    # Check 'Reduced membership' method selected.
    mode_red_memb, local_bin, min_prob = g.rm_params
    if mode_red_memb not in {'local', 'n_memb', 'mp_05', 'top_h', 'man', 'mag',
                             'skip'}:
        sys.exit("ERROR: the selected reduced membership method ('{}')"
                 " does\nnot match a valid input.".format(mode_red_memb))
    # Check binning if 'local' method was selected.
    bin_methods_dict = {'blocks', 'knuth', 'scott', 'freedman', 'sturges',
                        'sqrt', 'bb'}
    if mode_red_memb == 'local' and local_bin not in bin_methods_dict:
        sys.exit("ERROR: the selected binning method '{}' for the 'Reduced"
                 "\nmembership' function does not match a valid input."
                 .format(local_bin))

    # Unpack.
    bf_flag, best_fit_algor, lkl_method, bin_method, N_b = g.bf_params

    # If best fit method is set to run.
    ip_list = []
    if bf_flag:

        # Check best fit method selected.
        if best_fit_algor not in {'brute', 'genet'}:
            sys.exit("ERROR: the selected best fit method '{}' does not match"
                     " a valid input.".format(best_fit_algor))

        if best_fit_algor == 'genet':
            # Check GA input params.
            n_pop, n_gen, fdif, p_cross, cr_sel, p_mut, n_el, n_ei, n_es = \
                g.ga_params
            # First set of params.
            oper_dict0 = {'n_pop': n_pop, 'n_gen': n_gen, 'n_el': n_el,
                          'n_ei': n_ei, 'n_es': n_es}
            for oper in oper_dict0:
                if oper_dict0[oper] < 1:
                    sys.exit("ERROR: number must be greater than zero in\n"
                             "'{}' GA parameter; {} is set.".format(
                                oper, oper_dict0[oper]))
            # Second set of params.
            oper_dict1 = {'fdif': fdif, 'p_cross': p_cross, 'p_mut': p_mut}
            for oper in oper_dict1:
                if oper_dict1[oper] < 0. or oper_dict1[oper] > 1.:
                    sys.exit("ERROR: GA '{}' parameter is out of the valid\n"
                             "[0., 1.] range; {} is set.".format(
                                oper, oper_dict1[oper]))
            # Handle separately.
            if cr_sel not in {'1P', '2P'}:
                sys.exit("ERROR: GA 'cr_sel' operator is not a valid choice;\n"
                         "'{}' is set.".format(cr_sel))
            # Number of solutions to pass to the nest generation (elitism)
            if n_el >= n_pop:
                sys.exit("ERROR: GA 'n_el' must be smaller than 'n_pop';\n"
                         "'{}' and '{}' are set respectively.".format(
                            n_el, n_pop))

        # Check likelihood method selected.
        if lkl_method not in {'tolstoy', 'dolphin'}:
            sys.exit("ERROR: the selected likelihood method '{}' does not"
                     " match a valid input.".format(lkl_method))

        # Check binning method selected.
        if lkl_method == 'dolphin' and bin_method not in bin_methods_dict:
            sys.exit("ERROR: the selected binning method '{}' for the 'Best"
                     "\nfit' function does not match a valid input."
                     .format(bin_method))

        # Unpack.
        iso_path = g.ps_params[0]
        iso_select, par_ranges = g.ps_params[2:]

        # Check if /isochrones folder exists.
        if not isdir(iso_path):
            sys.exit("ERROR: 'Best synthetic cluster fit' function is set to"
                     " run but the folder:\n\n {}\n\ndoes not exists."
                     .format(iso_path))

        # Check IMF defined.
        imfs_dict = {'chabrier_2001_exp', 'chabrier_2001_log', 'kroupa_1993',
                     'kroupa_2002'}
        if g.sc_params[0] not in imfs_dict:
            sys.exit("ERROR: Name of IMF ({}) is incorrect.".format(
                g.sc_params[0]))

        # Check binarity parameters.
        # See if it is a list of values or a range.
        if par_ranges[-1][0] == 'r':
            if len(par_ranges[-1][-1]) > 1:
                # Range: min, max, step. Store min and max in array.
                bin_fr = np.array([par_ranges[-1][-1][0],
                                  par_ranges[-1][-1][1]])
            else:
                # Single value stored.
                bin_fr = np.array([par_ranges[-1][-1][0]])
        else:
            # List: store all values in array.
            bin_fr = np.array(par_ranges[-1][-1])
        # Check all values in array.
        for bin_fr_val in bin_fr:
            if bin_fr_val > 1.:
                sys.exit("ERROR: Binarity fraction value '{}' is out of\n"
                         "boundaries. Please select a value in the range "
                         "[0., 1.]".format(bin_fr_val))
        if g.sc_params[-1] > 1.:
            sys.exit("ERROR: Binary mass ratio set ('{}') is out of\n"
                     "boundaries. Please select a value in the range [0., 1.]".
                     format(g.sc_params[-1]))

        # Check selected isochrones set.
        if iso_select not in {'PAR10', 'PAR11', 'PAR12'}:
            sys.exit("ERROR: the selected isochrones set ('{}') does\n"
                     "not match a valid input.".format(iso_select))

        # Check that no parameter range is empty.
        global mass_rs
        m_rs, a_rs, e_rs, d_rs, mass_rs, bin_rs = par_ranges
        p_names = [['metallicity', m_rs], ['age', a_rs], ['extinction', e_rs],
                   ['distance', d_rs], ['mass', mass_rs], ['binary', bin_rs]]
        if min(mass_rs[1]) == 0:
            print("WARNING: minimum total mass is zero in input params file.")
            if 10 in mass_rs[1]:
                print("Removing zero value from mass array.\n")
                del mass_rs[1][mass_rs[1].index(0)]
            else:
                print("Changed minimum mass to 10.\n")
                mass_rs[1][mass_rs[1].index(min(mass_rs[1]))] = 10.

        for i, p in enumerate(par_ranges):
            # Catch empty list.
            if not p:
                sys.exit("ERROR: Range defined for '{}' parameter is"
                         " empty".format(p_names[i][0]))
            # Catch *almost* empty list since get_in_params perhaps added
            # an identificator 'l' or 'r'. This prevents ranges given as
            # empty lists (ie: [] or () or {}) from passing as valid ranges.
            elif not p[1]:
                sys.exit("ERROR: Range defined for '{}' parameter is"
                         " empty".format(p_names[i][0]))

        # Get parameters values defined.
        param_ranges, met_f_filter, met_values, age_values = \
            get_m_a_vls(iso_path)
        # Check that ranges are properly defined.
        for i, p in enumerate(param_ranges):
            if not p.size:
                sys.exit("ERROR: No values exist for '{}' range defined:\n\n"
                         "min={}, max={}, step={}".format(p_names[i][0],
                                                          *p_names[i][1][1]))

        # Check that metallicity and age min, max & steps values are correct.
        # Match values in metallicity and age ranges with those available.
        z_range, a_range = param_ranges[:2]

        if len(z_range) > len(met_values):
            # Find missing elements.
            missing = find_missing(z_range, met_values)
            sys.exit("ERROR: one or more metallicity files could not be\n"
                     "matched to the range given.\nThe range defined was:\n\n"
                     "{}\n\nand the closest available values are:\n\n"
                     "{}\n\nThe missing elements are:\n\n{}".format(
                        z_range, np.asarray(met_values), missing))
        if len(a_range) > len(age_values):
            # Find missing elements.
            missing = find_missing(a_range, age_values)
            sys.exit("ERROR: one or more isochrones could not be matched\n"
                     "to the age range given.\nThe range defined was:\n\n"
                     "{}\n\nand the closest available values are:\n\n"
                     "{}\n\nThe missing elements are:\n\n{}".format(
                        a_range, np.asarray(age_values), missing))

        # Read metallicity files.
        try:
            # Store all isochrones in all the metallicity files in isoch_list.
            ip_list = isochp.ip()
        except:
            print traceback.format_exc()
            sys.exit("ERROR: unknown error reading metallicity files.")

    print 'Full check done.\n'

    # Force matplotlib to not use any Xwindows backend. This call prevents
    # the code from crashing when used in a computer cluster. See:
    # http://stackoverflow.com/a/3054314/1391441
    if g.flag_back_force:
        import matplotlib
        matplotlib.use('Agg')
        print "(Force matplotlib to not use any Xwindows backend)\n"

    return ip_list, R_in_place
