
// br_gh800 (github Issue #800)
module AssignLiterals;
    initial begin
        string s;

        s = "A\0B";
        $display("1. '%s' len=%1d hex=%02h%02h%02h",s,s.len(), s[0], s[1], s[2]);

        s = "A\015\12B";
        $display("2. '%s' len=%1d hex=%02h%02h%02h%02h",s,s.len(), s[0], s[1], s[2], s[3]);

        s = {"A","\015","\012","B"};
        $display("3. '%s' len=%1d hex=%02h%02h%02h%02h",s,s.len(),
		 s[0], s[1], s[2], s[3]);

        s = "A\170\171B";
        $display("4. '%s' len=%1d hex=%02h%02h%02h%02h",s,s.len(),
		 s[0], s[1], s[2], s[3]);

        s = {"A",8'o15,8'o12,"\012","B"};
        $display("5. '%s' len=%1d hex=%02h%02h%02h%02h%02h",s,s.len(),
		 s[0], s[1], s[2], s[3], s[4]);
    end
endmodule
