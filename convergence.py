"""Main function for convergence tracker."""


class ConvergenceTrackerQE(object):
    def __init__(self, input_file, ecutwfc):
        self.input_file = input_file
        self.ecutwfc = ecutwfc

    def _edit_input(self):
        """Function to edit qe input script."""
        # Get the input.
        with open(self.input_file, 'r') as f:
            self.input_data = f.readlines()

        # Find the correct line to edit K_POINT values.
        for index, line in enumerate(self.input_data):
            # NOTE could be outside the loop for kpoints
            if 'ecutwfc' in line:
                ecutwfc_edit = index
            elif 'K_POINTS' in line:
                k_points_edit = index + 1
        # Edit desired on values.
        self._set_ecutwfc(ecutwfc_edit)
        self._iterate_kpoints(k_points_edit)

        # Write out the new file.
        with open('pw_scf_tmp.in', 'w') as f:
            f.write(''.join(self.input_data))

    def _set_ecutwfc(self, edit):
        """Function to edit ecutwfc."""
        s = self.input_data[edit].split(' ')
        s[-1] = '{}\n'.format(self.ecutwfc)
        self.input_data[edit] = ' '.join(s)

    def _iterate_kpoints(self, edit):
        """Function to iterate over k-points."""
        s = self.input_data[edit].split(' ')
        for k in range(3):
            s[k] = str(int(s[k]) + 1)
        self.input_data[edit] = ' '.join(s)

    def _scrape_output(self, output_file):
        """Function to get total energy from calculation output."""
        with open(output_file, 'r') as f:
            output_data = f.readlines()

        converged = False
        for i in output_data[::-1]:
            # Check for convergence of the calculation.
            if 'convergence has been achieved' in i:
                converged = True
            if 'total energy              =' in i:
                if not converged:
                    raise AssertionError('Calculation did not converge.')
                energy = float(i.split(' ')[-2])

        return energy


if __name__ == '__main__':
    ct = ConvergenceTrackerQE('pw_scf.in', 80)
    ct._edit_input()
    ct._scrape_output('pw-scf.out')
