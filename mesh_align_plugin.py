import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design.')
            return

        # Create a command input dialog for multiple selections
        # Get the command definitions
        cmdDefs = ui.commandDefinitions
        
        # Check if our command already exists, if so delete it
        cmdDef = cmdDefs.itemById('MeshAlignMulti')
        if cmdDef:
            cmdDef.deleteMe()
        
        # Create the command definition
        cmdDef = cmdDefs.addButtonDefinition(
            'MeshAlignMulti',
            'Align Mesh to Planes',
            'Select construction planes and target origin planes to align mesh bodies'
        )
        
        # Connect to the command created event
        onCommandCreated = MeshAlignCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        
        # Execute the command
        cmdDef.execute()
        
        # Prevent this module from being terminated when the script returns
        adsk.autoTerminate(False)
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Global list to keep handlers referenced for the duration of the command
handlers = []


class MeshAlignCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            
            eventArgs = adsk.core.CommandCreatedEventArgs.cast(args)
            cmd = eventArgs.command
            
            # Connect to the execute event
            onExecute = MeshAlignCommandExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
            
            # Connect to the destroy event
            onDestroy = MeshAlignCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)
            
            # Connect to the input changed event for auto-advancing selections
            onInputChanged = MeshAlignInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            handlers.append(onInputChanged)
            
            # Get the command inputs
            inputs = cmd.commandInputs
            
            # Add mesh body selection
            meshSel = inputs.addSelectionInput('meshSelection', 'Mesh Body', 'Select the mesh body to align')
            meshSel.addSelectionFilter('MeshBodies')
            meshSel.setSelectionLimits(1, 1)
            
            # Add source plane 1 selection
            src1 = inputs.addSelectionInput('srcPlane1', 'Source Plane 1', 'Select first construction plane on mesh')
            src1.addSelectionFilter('ConstructionPlanes')
            src1.setSelectionLimits(1, 1)
            
            # Add target plane 1 selection
            tgt1 = inputs.addSelectionInput('tgtPlane1', 'Target Plane 1', 'Select first target origin plane')
            tgt1.addSelectionFilter('ConstructionPlanes')
            tgt1.setSelectionLimits(1, 1)
            
            # Add source plane 2 selection (optional)
            src2 = inputs.addSelectionInput('srcPlane2', 'Source Plane 2 (Optional)', 'Select second construction plane on mesh')
            src2.addSelectionFilter('ConstructionPlanes')
            src2.setSelectionLimits(0, 1)
            
            # Add target plane 2 selection (optional)
            tgt2 = inputs.addSelectionInput('tgtPlane2', 'Target Plane 2 (Optional)', 'Select second target origin plane')
            tgt2.addSelectionFilter('ConstructionPlanes')
            tgt2.setSelectionLimits(0, 1)
            
            # Add preview checkbox
            # NOTE: preview UI is currently disabled (commented out).
            # If you want to re-enable Preview Mode later, uncomment the line below.
            # inputs.addBoolValueInput('previewMode', 'Preview Mode', True, '', False)
            
            # Add debug output checkbox
            inputs.addBoolValueInput('debugMode', 'Show Debug Info', True, '', False)
            
            # Add flip direction checkbox
            inputs.addBoolValueInput('flipDirection', 'Flip 180° on Plane 1', True, '', False)
            
            # Show a brief usage message before the user selects planes
            try:
                ui.messageBox(
                    'How to use this tool:\n\n'
                    '- Direct Edit Mesh\n'
                    "- Create Plane Through 3 Points (Create more if needed)\n\n"
                    'Select the mesh and then the source/target planes as prompted.',
                    'Mesh Align - Usage'
                )
            except:
                # Ignore any UI errors here; it's non-critical
                pass
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MeshAlignInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            changedInput = eventArgs.input
            inputs = eventArgs.inputs
            
            # Auto-advance to next selection when current one is filled
            if changedInput.id == 'meshSelection':
                meshSel = inputs.itemById('meshSelection')
                if meshSel.selectionCount > 0:
                    src1 = inputs.itemById('srcPlane1')
                    src1.hasFocus = True
                    
            elif changedInput.id == 'srcPlane1':
                src1 = inputs.itemById('srcPlane1')
                if src1.selectionCount > 0:
                    tgt1 = inputs.itemById('tgtPlane1')
                    tgt1.hasFocus = True
                    
            elif changedInput.id == 'tgtPlane1':
                tgt1 = inputs.itemById('tgtPlane1')
                if tgt1.selectionCount > 0:
                    src2 = inputs.itemById('srcPlane2')
                    src2.hasFocus = True
                    
            elif changedInput.id == 'srcPlane2':
                src2 = inputs.itemById('srcPlane2')
                if src2.selectionCount > 0:
                    tgt2 = inputs.itemById('tgtPlane2')
                    tgt2.hasFocus = True
                    
        except:
            pass


class MeshAlignCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            inputs = eventArgs.command.commandInputs
            
            # Get the mesh selection
            meshSel = inputs.itemById('meshSelection')
            if meshSel.selectionCount == 0:
                ui.messageBox('Please select a mesh body.')
                return
            mesh = adsk.fusion.MeshBody.cast(meshSel.selection(0).entity)
            
            # Get the first pair of planes
            src1Sel = inputs.itemById('srcPlane1')
            tgt1Sel = inputs.itemById('tgtPlane1')
            
            if src1Sel.selectionCount == 0 or tgt1Sel.selectionCount == 0:
                ui.messageBox('Please select both source and target planes for the first alignment.')
                return
            
            src_plane1 = adsk.fusion.ConstructionPlane.cast(src1Sel.selection(0).entity)
            tgt_plane1 = adsk.fusion.ConstructionPlane.cast(tgt1Sel.selection(0).entity)
            
            # Get the optional second pair of planes
            src2Sel = inputs.itemById('srcPlane2')
            tgt2Sel = inputs.itemById('tgtPlane2')
            
            src_plane2 = None
            tgt_plane2 = None
            
            if src2Sel.selectionCount > 0 and tgt2Sel.selectionCount > 0:
                src_plane2 = adsk.fusion.ConstructionPlane.cast(src2Sel.selection(0).entity)
                tgt_plane2 = adsk.fusion.ConstructionPlane.cast(tgt2Sel.selection(0).entity)
            
            # Preview mode input removed from UI; default to False.
            # If you re-enable the UI input above, restore these two lines:
            # previewInput = inputs.itemById('previewMode')
            # preview_mode = previewInput.value
            preview_mode = False
            
            # Get debug mode checkbox
            debugInput = inputs.itemById('debugMode')
            debug_mode = debugInput.value
            
            # Get flip direction checkbox
            flipInput = inputs.itemById('flipDirection')
            flip_direction = flipInput.value
            
            # Perform the alignment
            perform_alignment(mesh, src_plane1, tgt_plane1, src_plane2, tgt_plane2, ui, preview_mode, debug_mode, flip_direction)
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MeshAlignCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        adsk.autoTerminate(True)


def perform_alignment(mesh, src_plane1, tgt_plane1, src_plane2, tgt_plane2, ui, preview_mode=False, debug_mode=False, flip_direction=False):
    """Perform the mesh alignment based on selected planes"""
    move_feature = None
    try:
        if not mesh or not src_plane1 or not tgt_plane1:
            ui.messageBox('Invalid selections.')
            return
        
        src_geom1 = src_plane1.geometry
        tgt_geom1 = tgt_plane1.geometry
        
        if not src_geom1 or not tgt_geom1:
            ui.messageBox('Could not read geometry from planes.')
            return
        
        # Build debug output
        debug_info = 'DEBUG INFO\n' + '='*50 + '\n\n'
        
        debug_info += 'SOURCE PLANE 1 (Before):\n'
        debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
            src_geom1.origin.x, src_geom1.origin.y, src_geom1.origin.z)
        debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n'.format(
            src_geom1.normal.x, src_geom1.normal.y, src_geom1.normal.z)
        debug_info += '  uDirection: ({:.3f}, {:.3f}, {:.3f})\n'.format(
            src_geom1.uDirection.x, src_geom1.uDirection.y, src_geom1.uDirection.z)
        
        # Compute and log vDirection (perpendicular to both normal and uDirection)
        src_vDir = src_geom1.uDirection.crossProduct(src_geom1.normal)
        src_vDir.normalize()
        debug_info += '  vDirection: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
            src_vDir.x, src_vDir.y, src_vDir.z)
        
        debug_info += 'TARGET PLANE 1:\n'
        debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
            tgt_geom1.origin.x, tgt_geom1.origin.y, tgt_geom1.origin.z)
        debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n'.format(
            tgt_geom1.normal.x, tgt_geom1.normal.y, tgt_geom1.normal.z)
        debug_info += '  uDirection: ({:.3f}, {:.3f}, {:.3f})\n'.format(
            tgt_geom1.uDirection.x, tgt_geom1.uDirection.y, tgt_geom1.uDirection.z)
        
        tgt_vDir = tgt_geom1.uDirection.crossProduct(tgt_geom1.normal)
        tgt_vDir.normalize()
        debug_info += '  vDirection: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
            tgt_vDir.x, tgt_vDir.y, tgt_vDir.z)
        
        # If we have two plane pairs, use them to compute a more constrained alignment
        if src_plane2 and tgt_plane2:
            src_geom2 = src_plane2.geometry
            tgt_geom2 = tgt_plane2.geometry
            
            if src_geom2 and tgt_geom2:
                debug_info += 'SOURCE PLANE 2 (Before):\n'
                debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
                    src_geom2.origin.x, src_geom2.origin.y, src_geom2.origin.z)
                debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n'.format(
                    src_geom2.normal.x, src_geom2.normal.y, src_geom2.normal.z)
                debug_info += '  uDirection: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
                    src_geom2.uDirection.x, src_geom2.uDirection.y, src_geom2.uDirection.z)
                
                debug_info += 'TARGET PLANE 2:\n'
                debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
                    tgt_geom2.origin.x, tgt_geom2.origin.y, tgt_geom2.origin.z)
                debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
                    tgt_geom2.normal.x, tgt_geom2.normal.y, tgt_geom2.normal.z)
                
                # Log intersection axes
                src_intersection = src_geom1.normal.crossProduct(src_geom2.normal)
                src_intersection.normalize()
                tgt_intersection = tgt_geom1.normal.crossProduct(tgt_geom2.normal)
                tgt_intersection.normalize()
                
                debug_info += 'Source planes intersection axis: ({:.3f}, {:.3f}, {:.3f})\n'.format(
                    src_intersection.x, src_intersection.y, src_intersection.z)
                debug_info += 'Target planes intersection axis: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
                    tgt_intersection.x, tgt_intersection.y, tgt_intersection.z)
                
                # Use two-plane alignment for better control
                move_transform = compute_two_plane_transform(src_geom1, tgt_geom1, src_geom2, tgt_geom2)
                debug_info += 'Using TWO-PLANE alignment\n\n'
            else:
                # Fall back to single plane alignment
                move_transform = compute_single_plane_transform(src_geom1, tgt_geom1)
                debug_info += 'Using SINGLE-PLANE alignment (plane 2 geometry missing)\n\n'
        else:
            # Single plane alignment
            move_transform = compute_single_plane_transform(src_geom1, tgt_geom1)
            debug_info += 'Using SINGLE-PLANE alignment\n\n'
        
        # Apply 180-degree flip if requested (only for plane 1)
        flip_transform = None
        if flip_direction:
            # Compute where the source origin will be after the base transform
            src_origin_after_align = src_geom1.origin.copy()
            src_origin_after_align.transformBy(move_transform)

            # To flip 180°, rotate around an axis that lies IN the target plane (the uDirection)
            # CRITICAL: The rotation center must be OFFSET from the mesh origin, otherwise
            # rotating around an axis through the origin keeps the origin stationary
            # We'll offset along the plane's normal by a small amount to create a "hinge" effect
            flip_axis = tgt_geom1.uDirection.copy()
            try:
                flip_axis.normalize()
            except:
                pass
            
            # Create rotation center offset from the aligned origin
            # Move 10 units along the target plane normal to create a hinge point
            rotation_center = src_origin_after_align.copy()
            offset_vector = tgt_geom1.normal.copy()
            offset_vector.normalize()
            offset_vector.scaleBy(10.0)  # 10mm offset
            rotation_center.translateBy(offset_vector)
            
            flip_transform = adsk.core.Matrix3D.create()
            flip_transform.setToRotation(
                3.14159265359,  # 180 degrees in radians (pi)
                flip_axis,  # Rotation axis IN the plane (uDirection)
                rotation_center  # Rotation center OFFSET from mesh origin
            )

            # Do not combine here; apply flip as a separate move feature after the main move
            debug_info += 'Computed 180° FLIP transform around uDirection axis\n'
            debug_info += '  Flip axis: ({:.3f}, {:.3f}, {:.3f})\n'.format(
                flip_axis.x, flip_axis.y, flip_axis.z)
            debug_info += '  Rotation center (offset): ({:.2f}, {:.2f}, {:.2f})\n\n'.format(
                rotation_center.x, rotation_center.y, rotation_center.z)
        
        # Calculate where source plane 1 will move to
        src1_origin_transformed = src_geom1.origin.copy()
        src1_origin_transformed.transformBy(move_transform)
        
        src1_normal_transformed = src_geom1.normal.copy()
        src1_normal_transformed.transformBy(move_transform)
        
        debug_info += 'PREDICTED SOURCE PLANE 1 (After transform):\n'
        debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
            src1_origin_transformed.x, src1_origin_transformed.y, src1_origin_transformed.z)
        debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
            src1_normal_transformed.x, src1_normal_transformed.y, src1_normal_transformed.z)

        # If a flip was requested, compute and log predicted positions after the flip (without applying it)
        if flip_direction and flip_transform is not None:
            try:
                # Compute flip center (offset from source origin after alignment)
                flip_center = src_geom1.origin.copy()
                flip_center.transformBy(move_transform)
                offset_vector = tgt_geom1.normal.copy()
                offset_vector.normalize()
                offset_vector.scaleBy(10.0)
                flip_center.translateBy(offset_vector)

                debug_info += 'FLIP (planned) center (offset): ({:.2f}, {:.2f}, {:.2f})\n'.format(
                    flip_center.x, flip_center.y, flip_center.z)

                # Predict source plane 1 after flip by applying flip_transform to the already-transformed points
                src1_origin_postflip = src1_origin_transformed.copy()
                src1_origin_postflip.transformBy(flip_transform)
                src1_normal_postflip = src1_normal_transformed.copy()
                src1_normal_postflip.transformBy(flip_transform)

                debug_info += 'PREDICTED SOURCE PLANE 1 (After flip):\n'
                debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
                    src1_origin_postflip.x, src1_origin_postflip.y, src1_origin_postflip.z)
                debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
                    src1_normal_postflip.x, src1_normal_postflip.y, src1_normal_postflip.z)
            except Exception:
                debug_info += 'Failed to compute predicted post-flip positions: {}\n\n'.format(traceback.format_exc())
        
        if src_plane2 and tgt_plane2 and src_geom2:
            src2_origin_transformed = src_geom2.origin.copy()
            src2_origin_transformed.transformBy(move_transform)
            
            src2_normal_transformed = src_geom2.normal.copy()
            src2_normal_transformed.transformBy(move_transform)
            
            debug_info += 'PREDICTED SOURCE PLANE 2 (After transform):\n'
            debug_info += '  Origin: ({:.2f}, {:.2f}, {:.2f})\n'.format(
                src2_origin_transformed.x, src2_origin_transformed.y, src2_origin_transformed.z)
            debug_info += '  Normal: ({:.3f}, {:.3f}, {:.3f})\n\n'.format(
                src2_normal_transformed.x, src2_normal_transformed.y, src2_normal_transformed.z)
        
        # Calculate translation distance
        distance = src_geom1.origin.distanceTo(src1_origin_transformed)
        debug_info += 'Translation distance: {:.2f} mm\n\n'.format(distance)
        
        debug_info += '='*50 + '\n'

        # Skip if transform is effectively identity
        identity = adsk.core.Matrix3D.create()
        if _is_matrix_equal(move_transform, identity):
            ui.messageBox('Source plane already aligned to target plane. No action taken.')
            return

        parent_comp = mesh.parentComponent
        if not parent_comp:
            ui.messageBox('Could not determine parent component of the selected mesh.')
            return

        move_feats = parent_comp.features.moveFeatures
        ents = adsk.core.ObjectCollection.create()
        ents.add(mesh)

        # Create move feature input with the transform
        try:
            input_move = move_feats.createInput(ents, move_transform)
            move_feature = move_feats.add(input_move)
            flip_feature = None

            # If a flip transform was computed, add it as a second move feature (applies after the first)
            if flip_transform is not None:
                try:
                    input_flip = move_feats.createInput(ents, flip_transform)
                    flip_feature = move_feats.add(input_flip)
                    debug_info += 'Applied flip transform as second move feature\n\n'
                except Exception:
                    debug_info += 'Failed to add flip move feature: {}\n\n'.format(traceback.format_exc())
                    flip_feature = None

            # Preview-related user prompts removed. If debug is enabled, save debug info to file silently.
            if debug_mode:
                try:
                    import os
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    debug_file = os.path.join(script_dir, 'mesh_align_debug.txt')
                    with open(debug_file, 'w') as f:
                        f.write(debug_info)
                except:
                    # As a fallback, show debug info in a message box if file write fails
                    ui.messageBox(debug_info)
                # No success message when not in debug mode
                    
        except Exception:
            ui.messageBox('Failed to create and apply move feature:\n{}'.format(traceback.format_exc()))
            return
            
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def compute_single_plane_transform(src_geom, tgt_geom):
    """Compute transform to align one plane to another"""
    # Compute Z axes for both planes (perpendicular to the plane surface)
    src_z = src_geom.normal.crossProduct(src_geom.uDirection)
    src_z.normalize()
    
    tgt_z = tgt_geom.normal.crossProduct(tgt_geom.uDirection)
    tgt_z.normalize()
    
    # Create transform that aligns source plane coordinate system to target plane coordinate system
    move_transform = adsk.core.Matrix3D.create()
    move_transform.setToAlignCoordinateSystems(
        src_geom.origin,
        src_geom.uDirection,
        src_geom.normal,
        src_z,
        tgt_geom.origin,
        tgt_geom.uDirection,
        tgt_geom.normal,
        tgt_z
    )
    return move_transform


def compute_two_plane_transform(src_geom1, tgt_geom1, src_geom2, tgt_geom2):
    """Compute transform to align two planes simultaneously (more constrained)
    
    This computes a transform where:
    - Both source plane normals align with their respective target normals
    - The mesh is positioned so both planes pass through their target origins
    
    Strategy: Use the intersection line of the two planes as the primary alignment axis.
    """
    
    # Step 1: Compute the intersection line direction for both source and target plane pairs
    # The cross product of two plane normals gives the direction of their intersection line
    src_axis = src_geom1.normal.crossProduct(src_geom2.normal)
    src_axis.normalize()
    
    tgt_axis = tgt_geom1.normal.crossProduct(tgt_geom2.normal)
    tgt_axis.normalize()
    
    # Step 2: Build coordinate systems using intersection line and first plane normal
    # X = intersection direction, Y = plane1 normal, Z = X cross Y
    src_x = src_axis.copy()
    src_y = src_geom1.normal.copy()
    src_z = src_x.crossProduct(src_y)
    src_z.normalize()
    
    tgt_x = tgt_axis.copy()
    tgt_y = tgt_geom1.normal.copy()
    tgt_z = tgt_x.crossProduct(tgt_y)
    tgt_z.normalize()
    
    # Step 3: Use plane 1's origin as the reference point for translation
    # This ensures plane 1 origin aligns exactly with target 1 origin
    src_origin = src_geom1.origin.copy()
    tgt_origin = tgt_geom1.origin.copy()
    
    # Step 4: Create the transform using these coordinate systems
    move_transform = adsk.core.Matrix3D.create()
    move_transform.setToAlignCoordinateSystems(
        src_origin,
        src_x,
        src_y,
        src_z,
        tgt_origin,
        tgt_x,
        tgt_y,
        tgt_z
    )
    
    return move_transform


def _is_matrix_equal(m1, m2, tol=1e-6):
    """Compare two Matrix3D objects by transforming a set of points and
    checking they match within tolerance.
    """
    try:
        pts = [
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(1, 0, 0),
            adsk.core.Point3D.create(0, 1, 0),
            adsk.core.Point3D.create(0, 0, 1)
        ]
        for p in pts:
            a = p.copy()
            b = p.copy()
            a.transformBy(m1)
            b.transformBy(m2)
            if not _are_points_close(a, b, tol):
                return False
        return True
    except:
        return False


def _are_points_close(p1, p2, tol=1e-6):
    return (abs(p1.x - p2.x) <= tol and
            abs(p1.y - p2.y) <= tol and
            abs(p1.z - p2.z) <= tol)
