"""Main function for convergence tracker."""
from subprocess import call


class ConvergenceTracker(object):
    def __init__(self, input_file, output_file, kinetic_energy):
        self.input_file = input_file
        self.output_file = output_file
        self.kinetic_energy = kinetic_energy

        # Get the input.
        with open(self.input_file, 'r') as f:
            self.input_data = [line for line in f if not line.isspace()]

    def optimize(self, cutoff, param_list, initialize_kpts=False):
        """Function to optimize kpoint parameter."""
        if initialize_kpts:
            startk = self.get_start_params()
        else:
            startk = '1 1 1'
        var_list = [self.kinetic_energy, startk]
        self.edit_input(param_list, var_list)

        # Commit initial input.
        submit = call('cp files/pw-scf_1.out pw-scf.out', shell=True)
        if submit != 0:
            raise AssertionError('Could not submit job.')
        energy = self.scrape_output(self.output_file)

        converged = False
        index = 2  # just for test purposes.
        while not converged:
            # Setup a new input.
            kpts = self._iterate_kpoints(var_list[-1])
            var_list[-1] = kpts
            self.edit_input(param_list, var_list)

            # Run calculation.
            submit = call(
                'cp files/pw-scf_{}.out pw-scf.out'.format(index),
                shell=True)
            if submit != 0:
                raise AssertionError('Could not submit job.')
            new_energy = self.scrape_output(self.output_file)

            print('iteration {0} energy {1}'.format(index, new_energy))

            # Check for convergence.
            if abs(energy - new_energy) < cutoff:
                converged = True
            else:
                energy = new_energy
                index += 1

        return kpts

    def edit_input(self, param_list, var_list):
        """Function to edit qe input script."""
        self.update_input(param_list, var_list)
        # Write out the new file.
        with open('pw_scf.in', 'w') as f:
            f.write(''.join(self.input_data))

    def scrape_output(self, output_file, param='energy'):
        """Function to get total energy from calculation output."""
        with open(output_file, 'r') as f:
            output_data = f.readlines()

        self.check_calculation_convergence(output_data)
        res = eval('self.get_{}(output_data)'.format(param))

        return res

    def _iterate_kpoints(self, original, step=1):
        k = original.split(' ')
        for i in range(3):
            k[i] = str(int(k[i]) + step)

        return ' '.join(k)


class ConvergenceTrackerQE(ConvergenceTracker):
    def __init__(self, input_file, output_file, kinetic_energy):
        ConvergenceTracker.__init__(self, input_file, output_file,
                                    kinetic_energy)

    def update_input(self, param_list, var_list):
        """Function to edit qe input script."""
        # Find the correct lines to edit values.
        for index, line in enumerate(self.input_data):
            # NOTE could be outside the loop for kpoints
            if 'ecutwfc' in line:
                kinetic_energy_edit = index
            elif 'K_POINTS' in line:
                kpoints_edit = index + 1
        # Edit desired on values.
        for p, v in zip(param_list, var_list):
            eval('self._set_{0}({0}_edit, "{1}")'.format(p, v))

    def check_calculation_convergence(self, output_data):
        """Function to check that the calculation has converged."""
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
        """Function to get total energy from calculation output."""
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
        """Function to edit ecutwfc."""
        s = self.input_data[edit].split(' ')
        s[-1] = '{}\n'.format(energy)
        self.input_data[edit] = ' '.join(s)

    def _set_kpoints(self, edit, kpts):
        """Function to iterate over k-points."""
        s1 = self.input_data[edit].split(' ')
        s2 = kpts.split(' ')
        s = s2[:3] + s1[3:]
        self.input_data[edit] = ' '.join(s)


if __name__ == '__main__':
    ConvergenceTrackerQE('files/pw_scf.in', 'pw-scf.out', 80).optimize(
        cutoff=0.001, param_list=['kinetic_energy', 'kpoints'])
