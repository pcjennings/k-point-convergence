"""Main function for convergence tracker."""
from subprocess import call


class ConvergenceTracker(object):
    """Parent class for the convergence tracker."""

    def __init__(self, input_file, output_file, kinetic_energy=None):
        """Initialize class.

        Parameters
        ----------
        input_file : str
            Path to user defined input file.
        output_file : str
            Expected name of output file.
        kinetic_energy : int
            The kinetic energy cutoff for the wavefunctions.
        """
        self.input_file = input_file
        self.output_file = output_file
        self.kinetic_energy = kinetic_energy

        # Get the input.
        with open(self.input_file, 'r') as f:
            self.input_data = [line for line in f if not line.isspace()]

    def optimize(self, cutoff, param_list, initialize_kpts=False, step=1):
        """Function to optimize kpoint parameter.

        Parameters
        ----------
        cutoff : float
            Convergence criteria for change in total energy between sampling.
        param_list : list
            A list of parameters to change.
        initialize_kpts : bool
            Define whether to use the user defined K-points from the input
            script. If False, start from [1 1 1].
        step : int
            The step size to increase k-points.

        Returns
        -------
        kpts : str
           The string representation of the converged k-point dimensions
           (e.g. 5 5 5).
        """
        if initialize_kpts:
            startk = self.get_start_params()
        else:
            startk = '1 1 1'
        var_list = [self.kinetic_energy, startk]
        self.edit_input(param_list, var_list)

        # Commit initial input.
        energy = self.calculate(var_list)

        converged = False
        while not converged:
            # Setup a new input.
            kpts = self._iterate_kpoints(var_list[-1], step)
            var_list[-1] = kpts
            self.edit_input(param_list, var_list)

            # Run calculation.
            new_energy = self.calculate(var_list)

            # Check for convergence.
            if abs(energy - new_energy) < cutoff:
                converged = True
            else:
                energy = new_energy

        return kpts

    def edit_input(self, param_list, var_list):
        """Function to edit qe input script.

        Parameters
        ----------
        param_list : list
            A list of parameters to change.
        var_list : list
            A list of variables corresponding to the same order as the
            param_list.
        """
        self.update_input(param_list, var_list)
        # Write out the new file.
        with open('pw_scf.in', 'w') as f:
            f.write(''.join(self.input_data))

    def scrape_output(self, output_file, param='energy'):
        """Function to get total energy from calculation output.

        Parameters
        ----------
        output_file : str
            Expected output filename.
        param : str
            Parameter to return from output. Default is energy.

        Returns
        -------
        res : float
            The result from the output.
        """
        with open(output_file, 'r') as f:
            output_data = f.readlines()

        self.check_calculation_convergence(output_data)
        try:
            res = eval('self.get_{}(output_data)'.format(param))
        except AttributeError:
            raise NotImplementedError(
                'Finding parameter {} not implemented.'.format(param))

        return res

    def calculate(self, var_list):
        """Function to calculate the energy.

        Parameters
        ----------
        var_list : list
            A list of variables corresponding to the same order as the
            param_list.

        Returns
        -------
        energy : float
            The total energy from the output.
        """
        # Run dummy calculation.
        index = var_list[1].split(' ')[0]
        submit = call('cp files/pw-scf_{}.out pw-scf.out'.format(index),
                      shell=True)
        if submit != 0:
            raise AssertionError('Could not submit job.')
        energy = self.scrape_output(self.output_file)

        print('iteration {0} energy {1}'.format(index, energy))

        return energy

    def _iterate_kpoints(self, original, step):
        """Function to increase the number of k-points.

        Parameters
        ----------
        original : str
            The original k-point dimensions.
        step : int
            The step size to increase k-points.
        """
        k = original.split(' ')
        for i in range(3):
            k[i] = str(int(k[i]) + step)

        return ' '.join(k)


class ConvergenceTrackerQE(ConvergenceTracker):
    """QE specific class for the convergence tracker."""

    def __init__(self, input_file, output_file, kinetic_energy):
        """Initialize class.

        Parameters
        ----------
        input_file : str
            Path to user defined input file.
        output_file : str
            Expected name of output file.
        kinetic_energy : int
            The kinetic energy cutoff for the wavefunctions.
        """
        ConvergenceTracker.__init__(self, input_file, output_file,
                                    kinetic_energy)

    def update_input(self, param_list, var_list):
        """Function to edit qe input script.

        Parameters
        ----------
        param_list : list
            A list of parameters to change.
        var_list : list
            A list of variables corresponding to the same order as the
            param_list.
        """
        # Find the correct lines to edit values.
        for index, line in enumerate(self.input_data):
            if 'ecutwfc' in line:
                kinetic_energy_edit = index
            elif 'K_POINTS' in line:
                kpoints_edit = index + 1
        # Edit desired on values.
        for p, v in zip(param_list, var_list):
            eval('self._set_{0}({0}_edit, "{1}")'.format(p, v))

    def check_calculation_convergence(self, output_data):
        """Function to check that the calculation has converged.

        Parameters
        ----------
        output_data : list
            Data read in from the output file.
        """
        converged = False
        rev = output_data[::-1]
        for i in rev:
            # Check for convergence of the calculation.
            if 'convergence has been achieved' in i:
                break
            if 'total energy              =' in i:
                if not converged:
                    raise AssertionError('Calculation did not converge.')

    def get_energy(self, output_data):
        """Function to get total energy from calculation output.

        Parameters
        ----------
        output_data : list
            Data read in from the output file.
        """
        rev = output_data[::-1]
        for i in rev:
            if 'total energy              =' in i:
                return float(i.split(' ')[-2])

    def get_start_params(self):
        """Get user defined kpoints."""
        for index, line in enumerate(self.input_data):
            if 'K_POINTS' in line:
                kpoints = self.input_data[index + 1].split(' ')
                return ' '.join(kpoints[:3])

    def _set_kinetic_energy(self, edit, energy):
        """Function to edit ecutwfc.

        Parameters
        ----------
        edit : int
            Line index to edit.
        energy : int
            Kinetic energy cutoff for the wavefunctions.
        """
        s = self.input_data[edit].split(' ')
        s[-1] = '{}\n'.format(energy)
        self.input_data[edit] = ' '.join(s)

    def _set_kpoints(self, edit, kpts):
        """Function to iterate over k-points.

        Parameters
        ----------
        edit : int
            Line index to edit.
        kpts : str
            The k-point dimensions e.g. 1 1 1.
        """
        s1 = self.input_data[edit].split(' ')
        s2 = kpts.split(' ')
        s = s2[:3] + s1[3:]
        self.input_data[edit] = ' '.join(s)


if __name__ == '__main__':
    ConvergenceTrackerQE('files/pw_scf.in', 'pw-scf.out', 80).optimize(
        cutoff=0.001,
        param_list=['kinetic_energy', 'kpoints'],
        initialize_kpts=False,
        step=1
    )
