"""Production guard follows the frozen diagnostic contract."""
from unittest.mock import patch
import test_rigid_ambiguity as contract
from pfe_events import rigid_ambiguity


class ProductionGuardTests(contract.AmbiguityContractTests):
    def run_models(self, *models):
        with patch.object(rigid_ambiguity, 'estimate_rigid_motion', side_effect=models) as fit:
            result = rigid_ambiguity.guarded_rigid_motion(
                self.p, self.p, self.z, self.k, **self.times)
        return result, fit
