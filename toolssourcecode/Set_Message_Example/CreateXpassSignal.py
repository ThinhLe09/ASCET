from win32com.client import Dispatch
import traceback
from typing import Dict, Any, List, Optional, Tuple, Union

class AscetXPassUpdater:
    """
    用于定位XPass元素并更新ASCET数据库中信号实现信息的类
    Class to locate XPass elements and update signal implementation information in ASCET database
    """
    
    def __init__(self, ascet_version="6.1.4"):
        """
        使用指定版本初始化ASCET XPass更新器
        
        参数:
            ascet_version: ASCET版本字符串
        """
        self.ascet_version = ascet_version  # ASCET版本
        self.ascet = None                   # ASCET COM对象
        self.ascet_db = None                # ASCET数据库对象
        self.project = None                 # 当前项目对象
        self.project_formulas = None        # 项目公式列表
        self.connected = False              # 连接状态标志
        
    def connect(self):
        """
        连接到ASCET并获取当前数据库
        
        返回:
            bool: 连接成功状态
        """
        try:
            print(f"正在连接到ASCET {self.ascet_version}...")
            # 使用COM接口连接到ASCET
            self.ascet = Dispatch(f"Ascet.Ascet.{self.ascet_version}")
            if not self.ascet:
                print("无法连接到ASCET API")
                return False
                
            # 获取当前数据库
            self.ascet_db = self.ascet.GetCurrentDataBase()
            if not self.ascet_db:
                print("无法获取当前数据库")
                return False
                
            print(f"成功连接到ASCET {self.ascet_version}")
            print(f"当前数据库: {self.ascet_db.GetName()}")
            self.connected = True
            return True
        except Exception as e:
            print(f"连接ASCET时出错: {str(e)}")
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """
        断开与ASCET的连接
        """
        if self.connected and self.ascet:
            try:
                self.ascet.DisconnectFromTool()
                print("已断开与ASCET的连接")
            except Exception as e:
                print(f"断开ASCET连接时出错: {str(e)}")
    
    def check_access_capabilities(self, item_obj):
        """
        检查对象支持的访问方法
        
        参数:
            item_obj: 要检查的对象
            
        返回:
            dict: 支持的访问方法字典
        """
        if not item_obj:
            return {}
            
        capabilities = {}
        
        # 检查数据库访问权限方法
        capabilities['has_set_read'] = hasattr(item_obj, 'SetAccessRightRead')
        capabilities['has_set_write'] = hasattr(item_obj, 'SetAccessRightWrite')
        capabilities['has_set_code_gen'] = hasattr(item_obj, 'SetAccessRightCodeGeneration')
        capabilities['has_set_execute'] = hasattr(item_obj, 'SetAccessRightExecute')
        capabilities['has_set_application'] = hasattr(item_obj, 'SetAccessRightApplication')
        
        # 检查信号特定的访问方法
        capabilities['has_could_enable_set'] = hasattr(item_obj, 'CouldEnableSetAccess')
        capabilities['has_enable_set'] = hasattr(item_obj, 'EnableSetAccess')
        capabilities['has_disable_set'] = hasattr(item_obj, 'DisableSetAccess')
        
        # 检查事务支持
        capabilities['has_begin_transaction'] = hasattr(item_obj, 'BeginTransaction')
        capabilities['has_commit_transaction'] = hasattr(item_obj, 'CommitTransaction')
        capabilities['has_abort_transaction'] = hasattr(item_obj, 'AbortTransaction')
        
        # 打印支持的功能
        supported = [k for k, v in capabilities.items() if v]
        if supported:
            print(f"对象支持的访问方法: {', '.join(supported)}")
        else:
            print("对象不支持任何已知的访问方法")
            
        return capabilities
    
    def set_database_access_rights(self, item_obj, read=True, write=True, 
                                  code_gen=False, execute=False, application=False):
        """
        如果方法可用，则设置数据库项的访问权限
        
        参数:
            item_obj: 要设置访问权限的数据库项
            read: 是否启用读取访问
            write: 是否启用写入访问
            code_gen: 是否启用代码生成访问
            execute: 是否启用执行访问
            application: 是否启用应用程序访问
            
        返回:
            bool: 操作的成功状态
        """
        if not item_obj:
            print("未提供数据库项")
            return False
            
        try:
            success = True
            results = {}
            
            # 获取对象类型和功能
            obj_type = str(type(item_obj).__name__) if hasattr(item_obj, "__class__") else "Unknown"
            capabilities = self.check_access_capabilities(item_obj)
            
            # 仅在方法存在时尝试设置权限
            if capabilities.get('has_set_read', False):
                read_result = item_obj.SetAccessRightRead(read)
                results['read'] = read_result
                success = success and read_result
                
            if capabilities.get('has_set_write', False):
                write_result = item_obj.SetAccessRightWrite(write)
                results['write'] = write_result
                success = success and write_result
                
            if capabilities.get('has_set_code_gen', False) and code_gen:
                codegen_result = item_obj.SetAccessRightCodeGeneration(code_gen)
                results['code_gen'] = codegen_result
                success = success and codegen_result
                
            if capabilities.get('has_set_execute', False) and execute:
                execute_result = item_obj.SetAccessRightExecute(execute)
                results['execute'] = execute_result
                success = success and execute_result
                
            if capabilities.get('has_set_application', False) and application:
                app_result = item_obj.SetAccessRightApplication(application)
                results['application'] = app_result
                success = success and app_result
                
            if results:
                print(f"设置访问权限结果: {results}")
            else:
                print(f"此{obj_type}对象上没有可用的访问权限方法")
                
            return success
        except Exception as e:
            print(f"设置访问权限时出错: {str(e)}")
            traceback.print_exc()
            return False
    
    def load_project(self, project_name, project_folder):
        """
        加载ASCET项目
        
        参数:
            project_name: 项目名称
            project_folder: 项目文件夹路径
            
        返回:
            bool: 加载成功状态
        """
        if not self.connected:
            print("未连接到ASCET")
            return False
            
        try:
            print(f"正在加载项目: {project_name} 从 {project_folder}")
            self.project = self.ascet_db.GetItemInFolder(project_name, project_folder)
            
            if not self.project:
                print(f"未找到项目: {project_name} 在 {project_folder}")
                return False
                
            print(f"成功加载项目: {self.project.GetName()}")
            
            # 加载项目中的所有公式
            self.project_formulas = self.project.GetAllFormulas()
            formula_count = len(self.project_formulas) if self.project_formulas else 0
            print(f"从项目中加载了 {formula_count} 个公式")
            
            return True
        except Exception as e:
            print(f"加载项目时出错: {str(e)}")
            traceback.print_exc()
            return False
            
    def locate_xpass_elements(self, start_folder_path):
        """
        在给定的起始路径下定位所有XPass元素
        
        参数:
            start_folder_path: 起始文件夹路径
            
        返回:
            list: 找到的XPass项目列表
        """
        try:
            print(f"\n正在定位 {start_folder_path} 下的所有XPass元素...")
            found_xpass_items = []
            
            # 扫描文件夹结构
            result = self.scan_folder(start_folder_path)
            if not result:
                print(f"扫描文件夹失败: {start_folder_path}")
                return []
            
            # 递归处理文件夹数据
            self.process_folder_data(result, found_xpass_items)
            
            print(f"\n找到 {len(found_xpass_items)} 个XPass项目")
            for i, item in enumerate(found_xpass_items, 1):
                print(f"  {i}. {item['name']} 位于 {item['path']}")
                
            return found_xpass_items
            
        except Exception as e:
            print(f"定位XPass元素时出错: {str(e)}")
            traceback.print_exc()
            return []
    
    def scan_folder(self, folder_path):
        """
        扫描ASCET数据库中的特定文件夹
        
        参数:
            folder_path: 文件夹路径
            
        返回:
            dict: 扫描结果数据
        """
        try:
            print(f"扫描文件夹: {folder_path}")
            
            # 规范化路径格式
            normalized_path = folder_path.replace('/', '\\')
            if normalized_path.startswith('\\'):
                normalized_path = normalized_path[1:]
            
            # 获取文件夹组件
            path_components = normalized_path.split('\\')
            current_folder = None
            
            # 导航到指定的文件夹
            for i, component in enumerate(path_components):
                if i == 0:
                    # 第一个组件 - 从顶层获取
                    current_folder = self.ascet_db.GetFolder(component)
                    if not current_folder:
                        print(f"找不到顶层文件夹: {component}")
                        return {}
                else:
                    # 后续组件 - 从当前文件夹获取
                    parent_path = '\\'.join(path_components[:i])
                    next_folder = self.ascet_db.GetItemInFolder(component, parent_path)
                    if not next_folder:
                        print(f"找不到子文件夹: {component} 在 {parent_path}")
                        return {}
                    current_folder = next_folder
            
            if not current_folder:
                print(f"无法导航到文件夹: {folder_path}")
                return {}
                
            # 获取文件夹中的所有项目
            result = {
                'folder': current_folder,
                'path': normalized_path,
                'subfolders': [],
                'classes': [],
                'elements': []
            }
            
            # 扫描子文件夹
            if hasattr(current_folder, 'GetSubFolders'):
                subfolders = current_folder.GetSubFolders()
                if subfolders:
                    for subfolder in subfolders:
                        if subfolder:
                            subfolder_name = subfolder.GetName()
                            subfolder_path = f"{normalized_path}\\{subfolder_name}"
                            result['subfolders'].append({
                                'name': subfolder_name,
                                'path': subfolder_path,
                                'object': subfolder
                            })
            
            # 扫描类和其他元素
            if hasattr(current_folder, 'GetAllDataBaseItems'):
                items = current_folder.GetAllDataBaseItems()
                if items:
                    for item in items:
                        if not item:
                            continue
                            
                        item_name = item.GetName()
                        item_path = f"{normalized_path}\\{item_name}"
                        
                        # 检查它是否是可遍历的容器
                        is_container = False
                        if hasattr(item, 'IsFolder'):
                            is_container = item.IsFolder()
                        
                        # Component和Config容器的特殊处理
                        if not is_container and item_name in ["Component", "Config"]:
                            is_container = True
                            
                        if is_container:
                            # 作为子文件夹处理
                            result['subfolders'].append({
                                'name': item_name,
                                'path': item_path,
                                'object': item
                            })
                        # 检查它是否是一个类
                        elif hasattr(item, 'IsClass') and item.IsClass():
                            result['classes'].append({
                                'name': item_name,
                                'path': item_path,
                                'object': item
                            })
                        else:
                            result['elements'].append({
                                'name': item_name,
                                'path': item_path,
                                'object': item
                            })
            
            # 检查Package文件夹
            package_path = f"{normalized_path}\\Package"
            package_folder = self.ascet_db.GetItemInFolder("Package", normalized_path)
            if package_folder:
                result['subfolders'].append({
                    'name': "Package",
                    'path': package_path,
                    'object': package_folder
                })
            
            return result
                
        except Exception as e:
            print(f"扫描文件夹 {folder_path} 时出错: {str(e)}")
            traceback.print_exc()
            return {}
    
    def process_folder_data(self, folder_data, found_xpass_items):
        """
        处理文件夹数据以查找XPass元素
        
        参数:
            folder_data: 文件夹数据
            found_xpass_items: 找到的XPass项目列表（引用传递，将被修改）
        """
        # 处理类
        for class_item in folder_data.get('classes', []):
            self.check_xpass_item(class_item['object'], class_item['path'], found_xpass_items)
        
        # 处理元素
        for element_item in folder_data.get('elements', []):
            self.check_xpass_item(element_item['object'], element_item['path'], found_xpass_items)
        
        # 递归处理子文件夹
        for subfolder in folder_data.get('subfolders', []):
            subfolder_data = self.scan_folder(subfolder['path'])
            if subfolder_data:
                self.process_folder_data(subfolder_data, found_xpass_items)
    
    def check_xpass_item(self, item_obj, item_path, found_xpass_items):
        """
        检查项目是否是XPass项目
        
        参数:
            item_obj: 项目对象
            item_path: 项目路径
            found_xpass_items: 找到的XPass项目列表（引用传递，将被修改）
        """
        if not item_obj:
            return
            
        # 获取项目名称
        item_name = ""
        if hasattr(item_obj, 'GetName'):
            item_name = item_obj.GetName()
            
        # 检查名称是否包含XPass或匹配目标名称
        if "XPass" in item_name:
            print(f"找到XPass项目: {item_name} 位于 {item_path}")
            found_xpass_items.append({
                'name': item_name,
                'path': item_path,
                'object': item_obj
            })
        
        # 尝试获取表示类（如果适用）
        if hasattr(item_obj, 'GetRepresentedClass'):
            try:
                represented_class = item_obj.GetRepresentedClass()
                if represented_class and hasattr(represented_class, 'GetName'):
                    rep_name = represented_class.GetName()
                    if "XPass" in rep_name:
                        print(f"通过表示类找到XPass: {rep_name} 位于 {item_path}")
                        found_xpass_items.append({
                            'name': rep_name,
                            'path': item_path,
                            'object': item_obj
                        })
            except:
                pass
    
    def find_xpass_by_name(self, xpass_name, start_folder_path):
        """
        按名称查找特定XPass元素
        
        参数:
            xpass_name: XPass名称
            start_folder_path: 起始文件夹路径
            
        返回:
            dict: 找到的XPass项目，未找到时为None
        """
        print(f"正在搜索名称为: {xpass_name} 的XPass元素")
        all_xpass_items = self.locate_xpass_elements(start_folder_path)
        
        for item in all_xpass_items:
            if xpass_name in item['name']:
                print(f"找到匹配的XPass: {item['name']} 位于 {item['path']}")
                return item
        
        print(f"未找到匹配'{xpass_name}'的XPass")
        return None
    
    def find_signal(self, xpass_item, signal_name):
        """
        在XPass项目中查找信号
        
        参数:
            xpass_item: XPass项目
            signal_name: 信号名称
            
        返回:
            object: 找到的信号对象，未找到时为None
        """
        if not xpass_item:
            print("未提供XPass项目")
            return None
            
        try:
            # 获取XPass对象
            xpass_obj = xpass_item['object']
            target_module = xpass_obj
            
            # 尝试获取表示类（如果可用）
            if hasattr(xpass_obj, 'GetRepresentedClass'):
                represented_class = xpass_obj.GetRepresentedClass()
                if represented_class:
                    target_module = represented_class
                    print(f"使用表示类: {target_module.GetName()}")
            
            # 尝试获取具有信号名称的模型元素
            signal = None
            if hasattr(target_module, 'GetModelElement'):
                signal = target_module.GetModelElement(signal_name)
                
            if not signal:
                print(f"直接未找到信号: {signal_name}")
                
                # 尝试获取所有模型元素并搜索信号
                if hasattr(target_module, 'GetAllModelElements'):
                    all_elements = target_module.GetAllModelElements()
                    print(f"正在{len(all_elements)}个模型元素中搜索...")
                    
                    for element in all_elements:
                        try:
                            element_name = element.GetName()
                            if element_name == signal_name:
                                signal = element
                                print(f"通过完整搜索找到信号: {signal_name}")
                                break
                        except:
                            continue
                
            if not signal:
                print(f"在XPass模块中未找到信号: {signal_name}")
                return None
            
            # 检查它是否是消息
            if hasattr(signal, 'IsMessage') and not signal.IsMessage():
                print(f"找到的元素'{signal_name}'不是消息")
                return None
                
            print(f"找到信号: {signal.GetName()}")
            print(f"信号类型: {signal.GetModelType()}")
            print(f"是输入: {signal.IsReceiveMessage() if hasattr(signal, 'IsReceiveMessage') else '未知'}")
            print(f"是输出: {signal.IsSendMessage() if hasattr(signal, 'IsSendMessage') else '未知'}")
            
            return signal
        except Exception as e:
            print(f"查找信号时出错: {str(e)}")
            traceback.print_exc()
            return None
    
    def update_signal_impl_info(self, signal, target_impl_type=None, formula_name=None, 
                               impl_min=None, impl_max=None, limit_assignment=True, 
                               limit_overflow=True):
        """
        使用项目上下文和事务更新信号的实现信息
        
        参数:
            signal: 信号对象
            target_impl_type: 目标实现类型
            formula_name: 公式名称
            impl_min: 实现最小值
            impl_max: 实现最大值
            limit_assignment: 是否限制赋值
            limit_overflow: 是否限制溢出
            
        返回:
            bool: 更新成功状态
        """
        if not signal or not self.project:
            print("未提供信号或项目")
            return False
            
        try:
            print(f"\n更新信号的实现信息: {signal.GetName()}")
            
            # 首先开始事务 - 这对ASCET至关重要
            if hasattr(self.project, 'BeginTransaction'):
                self.project.BeginTransaction()
                print("开始实现更新事务")
            
            ### 变更: 获取信号的父模块 - 新增代码
            parent_module = None
            if hasattr(signal, 'GetParent'):
                parent_module = signal.GetParent()
                print(f"获取父模块: {parent_module.GetName() if hasattr(parent_module, 'GetName') else '未知'}")
            
            ### 变更: 使用类实现方法获取实现信息 - 这是主要改进
            impl_info = None
            if parent_module:
                # 从父模块获取类实现
                if hasattr(parent_module, 'GetClassImplementation'):
                    class_impl = parent_module.GetClassImplementation()
                    print("从父模块获取类实现")
                    
                    # 获取信号的标量实现
                    if hasattr(class_impl, 'GetItem'):
                        scalar_impl = class_impl.GetItem(signal)
                        print("获取信号的标量实现")
                        
                        # 获取实现信息
                        if hasattr(scalar_impl, 'GetImplInfoForValue'):
                            impl_info = scalar_impl.GetImplInfoForValue()
                            print("从标量实现获取实现信息")
            
            ### 变更: 仅在类实现方法失败时回退到直接实现 - 原始方法作为备用
            if not impl_info:
                print("类实现方法失败，回退到直接实现")
                impl = signal.GetImplementation()
                if not impl:
                    print("信号没有实现对象")
                    if hasattr(self.project, 'AbortTransaction'):
                        self.project.AbortTransaction()
                    return False
                    
                # 获取实现信息
                impl_info = impl.GetImplInfoForValue()
                
            if not impl_info:
                print("获取实现信息失败")
                if hasattr(self.project, 'AbortTransaction'):
                    self.project.AbortTransaction()
                return False
            
            # 检查实现信息功能
            self.check_access_capabilities(impl_info)
                
            # 获取当前设置以供参考
            current_impl_type = impl_info.GetImplType() if hasattr(impl_info, 'GetImplType') else "未知"
            current_formula = impl_info.GetFormulaName() if hasattr(impl_info, 'GetFormulaName') else "未知"
            current_range = impl_info.GetDoubleImplRange() if hasattr(impl_info, 'GetDoubleImplRange') else "未知"
            
            print("当前实现设置:")
            print(f"  实现类型: {current_impl_type}")
            print(f"  公式名称: {current_formula}")
            print(f"  实现范围: {current_range}")
            
            # 步骤1: 首先设置限制赋值（对范围约束至关重要）
            if hasattr(impl_info, 'SetOptionLimitAssignment'):
                limit_assign_result = impl_info.SetOptionLimitAssignment(limit_assignment)
                print(f"设置选项限制赋值为 {limit_assignment}: {limit_assign_result}")
            
            # 步骤2: 将实现设为主控
            if hasattr(impl_info, 'SetMasterModel'):
                master_result = impl_info.SetMasterModel(False)  # False = 实现为主控
                print(f"将实现设为主控: {master_result}")
                
            # 步骤3: 设置实现类型
            if target_impl_type and hasattr(impl_info, 'SetImplType'):
                type_result = impl_info.SetImplType(target_impl_type)
                print(f"设置实现类型为 {target_impl_type}: {type_result}")
            
            # 步骤4: 设置公式
            if formula_name and self.project_formulas:
                formula_object = None
                for formula in self.project_formulas:
                    try:
                        if formula.GetName() == formula_name:
                            formula_object = formula
                            break
                    except:
                        continue
                
                if formula_object:
                    print(f"找到公式对象: {formula_name}")
                    if hasattr(impl_info, 'SetFormula'):
                        formula_result = impl_info.SetFormula(formula_object)
                        print(f"设置公式为 {formula_name}: {formula_result}")
                else:
                    print(f"未找到公式: {formula_name}")
            
            # 步骤5: 设置实现范围
            if impl_min is not None and impl_max is not None:
                impl_range = (float(impl_min), float(impl_max))
                print(f"设置实现范围为: {impl_range}")
                
                if hasattr(impl_info, 'SetDoubleImplRange'):
                    range_result = impl_info.SetDoubleImplRange(impl_range)
                    print(f"设置双精度实现范围: {range_result}")
            
            # 步骤6: 设置溢出选项
            if hasattr(impl_info, 'SetOptionLimitOverflow'):
                overflow_result = impl_info.SetOptionLimitOverflow(limit_overflow)
                print(f"设置选项限制溢出为 {limit_overflow}: {overflow_result}")
            
            ### 变更: 在项目上下文中更新 - 添加了多种更新方法
            # 首先尝试类实现更新方法
            if parent_module and hasattr(parent_module, 'GetClassImplementation'):
                class_impl = parent_module.GetClassImplementation()
                if hasattr(class_impl, 'UpdateItems'):
                    update_result = class_impl.UpdateItems()
                    print(f"通过类实现更新实现信息: {update_result}")
                # 同时尝试项目上下文
                if hasattr(class_impl, 'UpdateItemsInProject') and self.project:
                    project_update_result = class_impl.UpdateItemsInProject(self.project)
                    print(f"在项目上下文中更新实现信息: {project_update_result}")
            # 回退到直接实现更新
            elif hasattr(impl_info, 'UpdateInProject') and self.project:
                update_result = impl_info.UpdateInProject(self.project)
                print(f"直接在项目上下文中更新实现信息: {update_result}")
            
            # 提交事务
            if hasattr(self.project, 'CommitTransaction'):
                commit_result = self.project.CommitTransaction()
                print(f"提交事务: {commit_result}")
            
            ### 变更: 验证更新 - 使用相同的方法重新获取信息
            # 重新获取实现信息以验证更改
            verify_impl_info = None
            
            # 首先尝试类实现方法
            if parent_module and hasattr(parent_module, 'GetClassImplementation'):
                class_impl = parent_module.GetClassImplementation()
                if hasattr(class_impl, 'GetItem'):
                    scalar_impl = class_impl.GetItem(signal)
                    if hasattr(scalar_impl, 'GetImplInfoForValue'):
                        verify_impl_info = scalar_impl.GetImplInfoForValue()
            
            # 回退到直接实现
            if not verify_impl_info:
                impl = signal.GetImplementation()
                if impl and hasattr(impl, 'GetImplInfoForValue'):
                    verify_impl_info = impl.GetImplInfoForValue()
            
            if verify_impl_info:
                updated_impl_type = verify_impl_info.GetImplType() if hasattr(verify_impl_info, 'GetImplType') else "未知"
                updated_formula = verify_impl_info.GetFormulaName() if hasattr(verify_impl_info, 'GetFormulaName') else "未知"
                updated_range = verify_impl_info.GetDoubleImplRange() if hasattr(verify_impl_info, 'GetDoubleImplRange') else "未知"
                
                print("\n验证实现设置:")
                print(f"  实现类型: {updated_impl_type}")
                print(f"  公式名称: {updated_formula}")
                print(f"  实现范围: {updated_range}")
                
                # 验证是否应用了更改
                success = True
                if target_impl_type and updated_impl_type != target_impl_type:
                    print(f"警告: 实现类型未更新为 {target_impl_type}")
                    success = False
                if formula_name and updated_formula != formula_name:
                    print(f"警告: 公式未更新为 {formula_name}")
                    success = False
                    
                return success
            else:
                print("无法在更新后验证实现设置")
                return False
                
        except Exception as e:
            print(f"更新信号实现信息时出错: {str(e)}")
            traceback.print_exc()
            
            # 如果发生错误，尝试中止事务
            if hasattr(self.project, 'AbortTransaction'):
                self.project.AbortTransaction()
                print("由于错误中止事务")
                
            return False
    
    def create_or_update_signal(self, xpass_item, signal_name, signal_type="cont", 
                              is_input=False, is_output=True, formula_name="FX", 
                              impl_type="uint8", impl_min=0, impl_max=16, comment=None):
        """
        在XPass模块中创建新信号或更新现有信号
        
        参数:
            xpass_item: XPass项目
            signal_name: 信号名称
            signal_type: 信号类型
            is_input: 是否为输入
            is_output: 是否为输出
            formula_name: 公式名称
            impl_type: 实现类型
            impl_min: 实现最小值
            impl_max: 实现最大值
            comment: 注释
            
        返回:
            bool: 创建/更新成功状态
        """
        if not xpass_item or not self.project:
            print("未提供XPass项目或项目")
            return False
            
        try:
            # 开始事务
            if hasattr(self.project, 'BeginTransaction'):
                self.project.BeginTransaction()
                print("开始信号创建事务")
                
            # 获取XPass对象
            xpass_obj = xpass_item['object']
            target_module = xpass_obj
            
            # 尝试获取表示类（如果可用）
            if hasattr(xpass_obj, 'GetRepresentedClass'):
                represented_class = xpass_obj.GetRepresentedClass()
                if represented_class:
                    target_module = represented_class
                    print(f"使用表示类: {target_module.GetName()}")
            
            # 检查模块功能
            self.check_access_capabilities(target_module)
            
            new_signal = None
            # 使用模块API方法从文档创建适当的消息类型
            if is_input and is_output:
                if hasattr(target_module, 'AddSendReceiveMessage'):
                    new_signal = target_module.AddSendReceiveMessage(signal_name)
                    print(f"创建发送/接收消息: {signal_name}")
            elif is_input:
                if hasattr(target_module, 'AddReceiveMessage'):
                    new_signal = target_module.AddReceiveMessage(signal_name)
                    print(f"创建接收消息: {signal_name}")
            elif is_output:
                if hasattr(target_module, 'AddSendMessage'):
                    new_signal = target_module.AddSendMessage(signal_name)
                    print(f"创建发送消息: {signal_name}")
            
            if not new_signal:
                print(f"创建新信号'{signal_name}'失败")
                if hasattr(self.project, 'AbortTransaction'):
                    self.project.AbortTransaction()
                return False
            
            # 设置信号属性
            if hasattr(new_signal, 'SetModelType'):
                type_result = new_signal.SetModelType(signal_type)
                print(f"设置模型类型为 {signal_type}: {type_result}")
            
            if comment and hasattr(new_signal, 'SetComment'):
                comment_result = new_signal.SetComment(comment)
                print(f"设置注释: {comment_result}")
            
            # 提交信号创建部分
            if hasattr(self.project, 'CommitTransaction'):
                commit_result = self.project.CommitTransaction()
                print(f"提交信号创建事务: {commit_result}")
            
            # 在单独的事务中更新实现信息
            impl_update_success = self.update_signal_impl_info(
                new_signal, 
                target_impl_type=impl_type,
                formula_name=formula_name,
                impl_min=impl_min,
                impl_max=impl_max
            )
            
            if impl_update_success:
                print(f"成功创建并配置信号'{signal_name}'")
            else:
                print(f"信号已创建但实现配置失败")
            
            return impl_update_success
            
        except Exception as e:
            print(f"创建或更新信号时出错: {str(e)}")
            traceback.print_exc()
            
            # 如果发生错误，尝试中止事务
            if hasattr(self.project, 'AbortTransaction'):
                self.project.AbortTransaction()
                print("由于错误中止事务")
                
            return False


def main():
    """更新信号实现信息的主函数"""
    # 定义ASCET版本
    ascet_version = "6.1.4"
    
     # 定义项目信息
    project_name = "SSP4SuspCustCL_ECU_CSW_BB00001"  
    project_folder = r"Customer\CC_CN\Package\SensorSignalProcessing\Component"
    
    # 定义XPass和信号信息
    xpass_name = "XPass_BB00000_SSP4SuspCustCL"  # 要查找的XPass
    start_folder_path = r"\Customer"  # 从此文件夹开始搜索
    signal_name = "ActGear_FA"  # 要更新的信号
    
    
    # 定义新的实现设置
    new_impl_type = "uint8"
    new_formula = "IDENTITY"
    new_impl_min = 0
    new_impl_max = 16
    
    # 初始化更新器
    updater = AscetXPassUpdater(ascet_version)
    
    try:
        # 连接到ASCET
        if not updater.connect():
            print("连接到ASCET失败。退出。")
            return
        
        # 加载项目
        if not updater.load_project(project_name, project_folder):
            print("加载项目失败。退出。")
            return
        
        # 查找XPass元素
        xpass_item = updater.find_xpass_by_name(xpass_name, start_folder_path)
        if not xpass_item:
            print(f"查找名称包含'{xpass_name}'的XPass失败。退出。")
            return
        
        # 查找信号
        signal = updater.find_signal(xpass_item, signal_name)
        if not signal:
            print(f"在XPass中查找信号'{signal_name}'失败。退出。")
            return
        
        # 更新信号实现信息
        success = updater.update_signal_impl_info(
            signal,
            target_impl_type=new_impl_type,
            formula_name=new_formula,
            impl_min=new_impl_min,
            impl_max=new_impl_max,
            limit_assignment=True,
            limit_overflow=True
        )
        
        if success:
            print(f"\n成功更新信号'{signal_name}'")
        else:
            print(f"\n更新信号'{signal_name}'失败")
        
    finally:
        # 断开与ASCET的连接
        updater.disconnect()


if __name__ == "__main__":
    main()