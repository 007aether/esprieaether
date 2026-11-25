// ESPRESSO SONNA G2 - exterior concept model Rev A
// Units: mm. W=750 is user-selected. H=500 and D=520 are provisional overall envelope.
// Feature locations and shell layout are illustrative. Not released for fabrication.
// No gas, burner, pressure vessel, water circuit, or electrical internals are modeled.

W=750; D=520; H=500; feet_h=20; skin=2; front_projection=30;
body_depth=D-front_projection;
group_centers=[255,535];
$fn=64;

module front_cyl(x,z,r,len,y0,clr) {
    color(clr) translate([x,y0,z]) rotate([90,0,0]) cylinder(h=len,r=r);
}
module shell() {
    color([0.77,0.80,0.83]) difference() {
        translate([0,front_projection,feet_h]) cube([W,body_depth,H-feet_h]);
        translate([skin,front_projection+skin,feet_h+skin]) cube([W-2*skin,body_depth-2*skin,H-feet_h-2*skin]);
    }
}
module feet() {
    color([0.18,0.21,0.24]) for (x=[35,W-65], y=[front_projection+35,D-65]) translate([x,y,0]) cube([30,30,feet_h]);
}
module face() {
    color([0.86,0.88,0.90]) translate([20,front_projection-3,95]) cube([W-40,3,310]);
    color([0.72,0.76,0.80]) translate([12,front_projection+12,H-3]) cube([W-24,body_depth-24,3]);
    color([0.42,0.47,0.52]) translate([40,0,68]) cube([W-80,front_projection,5]);
    for (x=group_centers) {
        front_cyl(x,270,45,24,front_projection,[0.72,0.76,0.79]);
        front_cyl(x,270,32,4,front_projection-24,[0.28,0.33,0.38]);
        front_cyl(x,270,18,2,front_projection-28,[0.78,0.81,0.84]);
        color([0.18,0.21,0.24]) hull() {
            translate([x,5,236]) sphere(r=5);
            translate([x+42,5,205]) sphere(r=5);
        }
        // Three manual labels; button positions are illustrative, not finalized.
        for (i=[0:2]) front_cyl(x-86,345-i*34,10,10,front_projection-3,[0.73,0.48,0.29]);
    }
    color([0.73,0.48,0.29]) translate([W/2,front_projection-4,430]) rotate([90,0,0]) linear_extrude(height=1)
        text("ESPRESSO SONNA",size=18,halign="center",font="Arial:style=Bold");
}
module side_seams() {
    color([0.65,0.69,0.73]) {
        translate([W-1,front_projection+body_depth*0.15,feet_h+70]) cube([1,body_depth*0.70,H-feet_h-150]);
        translate([W-1,front_projection+body_depth*0.15,feet_h+70]) cube([1,body_depth*0.70,2]);
    }
}
module model() { shell(); feet(); face(); side_seams(); }
model();