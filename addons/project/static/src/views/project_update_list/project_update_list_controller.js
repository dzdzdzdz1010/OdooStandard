import { ListController } from '@web/views/list/list_controller';
import { ProjectRightSidePanel } from '../../components/project_right_side_panel/project_right_side_panel';

export class ProjectUpdateListController extends ListController {
    static components = {
        ...ListController.components,
        ProjectRightSidePanel,
    };
    get className() {
        return super.className + ' o_controller_with_rightpanel';
    }
}
